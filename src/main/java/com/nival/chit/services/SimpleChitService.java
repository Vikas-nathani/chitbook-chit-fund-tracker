package com.nival.chit.services;

import com.nival.chit.dto.AddSimpleChitMemberDTO;
import com.nival.chit.dto.CreateSimpleChitDTO;
import com.nival.chit.dto.SavePayoutDTO;
import com.nival.chit.dto.SimpleChitDTO;
import com.nival.chit.dto.SimpleChitSummaryDTO;
import com.nival.chit.dto.UpdateSimpleChitDTO;
import com.nival.chit.entity.SimpleChit;
import com.nival.chit.entity.SimpleChitEntry;
import com.nival.chit.entity.SimpleChitMember;
import com.nival.chit.entity.SimpleChitPayout;
import com.nival.chit.entity.User;
import com.nival.chit.repository.SimpleChitRepository;
import com.nival.chit.security.AccessControlService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.YearMonth;
import java.time.format.DateTimeParseException;
import java.time.temporal.ChronoUnit;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * Business logic for owner-scoped simple chits (member names x months grid, payouts, P/L).
 *
 * <p>Scope rule: a chit is visible only to the user who created it. This lives here rather
 * than in {@link AccessControlService} because simple chits have no group membership to check;
 * every lookup goes through {@link #requireOwned(Long)}.</p>
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class SimpleChitService {

    private static final int MAX_MONTHS = 120;
    private static final int MAX_MEMBERS = 100;
    private static final int MAX_NAME_LENGTH = 100;
    private static final double DEFAULT_COMMISSION_PERCENT = 5;
    private static final double MAX_COMMISSION_PERCENT = 20;
    private static final double DEFAULT_ESCALATION_PERCENT = 1;

    private final SimpleChitRepository simpleChitRepository;
    private final AccessControlService accessControlService;

    /**
     * Create a chit. Every member's monthly entry = chit.perShareAmount * member.shares,
     * generated only from that member's startMonth through the chit's last month.
     */
    @Transactional
    public SimpleChitDTO create(CreateSimpleChitDTO dto) {
        User owner = accessControlService.getCurrentUser();

        String name = requireName(dto.getName(), "Chit name");
        double totalAmount = requirePositive(dto.getTotalAmount(), "Chit amount");
        int months = dto.getMonths() == null ? 0 : dto.getMonths();
        if (months < 1 || months > MAX_MONTHS) {
            throw new IllegalArgumentException("Months must be between 1 and " + MAX_MONTHS);
        }
        YearMonth startMonth = parseStartMonth(dto.getStartMonth());

        double perShareAmount = dto.getPerShareAmount() != null
                ? requirePositive(dto.getPerShareAmount(), "Amount per share")
                : BigDecimal.valueOf(totalAmount).divide(BigDecimal.valueOf(months), 2, RoundingMode.HALF_UP).doubleValue();

        List<CreateSimpleChitDTO.MemberInput> memberInputs = dto.getMembers() == null ? List.of() : dto.getMembers().stream()
                .filter(m -> m != null && m.getName() != null && !m.getName().trim().isEmpty())
                .toList();
        if (memberInputs.isEmpty() || memberInputs.size() > MAX_MEMBERS) {
            throw new IllegalArgumentException("Add between 1 and " + MAX_MEMBERS + " members");
        }

        boolean escalationEnabled = Boolean.TRUE.equals(dto.getEscalationEnabled());
        double escalationPercent = dto.getEscalationPercent() == null
                ? DEFAULT_ESCALATION_PERCENT
                : requirePercent(dto.getEscalationPercent(), "Escalation percent");

        SimpleChit chit = new SimpleChit();
        chit.setName(name);
        chit.setTotalAmount(totalAmount);
        chit.setMonths(months);
        chit.setStartMonth(startMonth.toString());
        chit.setPerShareAmount(perShareAmount);
        chit.setCommissionPercent(dto.getCommissionPercent() == null
                ? DEFAULT_COMMISSION_PERCENT
                : requireCommission(dto.getCommissionPercent()));
        chit.setEscalationEnabled(escalationEnabled);
        chit.setEscalationPercent(escalationPercent);
        chit.setOwner(owner);

        for (int i = 0; i < memberInputs.size(); i++) {
            CreateSimpleChitDTO.MemberInput input = memberInputs.get(i);
            String memberName = requireName(input.getName(), "Member name");
            int shares = requireShares(input.getShares());
            int startMonthIndex = resolveStartMonthIndex(startMonth, input.getStartMonth(), months, startMonth);
            addMemberToChit(chit, memberName, shares, startMonthIndex, i);
        }

        chit = simpleChitRepository.save(chit);
        log.info("Simple chit {} created by {}", chit.getId(), owner.getUsername());
        return toDTO(chit);
    }

    /**
     * Add a new member to an already-created chit. Their entries start at their own
     * start month (default: the current calendar month, clamped into the chit's range)
     * and run through the chit's last month.
     */
    @Transactional
    public SimpleChitDTO addMember(Long chitId, AddSimpleChitMemberDTO dto) {
        SimpleChit chit = requireOwned(chitId);
        String name = requireName(dto.getName(), "Member name");
        int shares = requireShares(dto.getShares());
        YearMonth chitStart = YearMonth.parse(chit.getStartMonth());
        YearMonth fallback = clampToChitRange(YearMonth.now(), chitStart, chit.getMonths());
        int startMonthIndex = resolveStartMonthIndex(chitStart, dto.getStartMonth(), chit.getMonths(), fallback);
        int position = chit.getMembers().stream().mapToInt(SimpleChitMember::getPosition).max().orElse(-1) + 1;

        addMemberToChit(chit, name, shares, startMonthIndex, position);

        chit = simpleChitRepository.saveAndFlush(chit);
        log.info("Member added to simple chit {}", chitId);
        return toDTO(chit);
    }

    private static void addMemberToChit(SimpleChit chit, String name, int shares, int startMonthIndex, int position) {
        SimpleChitMember member = new SimpleChitMember();
        member.setChit(chit);
        member.setName(name);
        member.setPosition(position);
        member.setShares(shares);
        member.setStartMonthIndex(startMonthIndex);

        double amount = BigDecimal.valueOf(chit.getPerShareAmount())
                .multiply(BigDecimal.valueOf(shares))
                .setScale(2, RoundingMode.HALF_UP)
                .doubleValue();
        for (int month = startMonthIndex; month <= chit.getMonths(); month++) {
            SimpleChitEntry entry = new SimpleChitEntry();
            entry.setMember(member);
            entry.setMonthIndex(month);
            entry.setAmount(amount);
            member.getEntries().add(entry);
        }
        chit.getMembers().add(member);
    }

    @Transactional(readOnly = true)
    public List<SimpleChitSummaryDTO> listMine() {
        YearMonth now = YearMonth.now();
        return findMine().stream()
                .map(chit -> SimpleChitMath.summary(chit, now))
                .collect(Collectors.toList());
    }

    /** All chits owned by the current user, newest first. */
    @Transactional(readOnly = true)
    public List<SimpleChit> findMine() {
        User owner = accessControlService.getCurrentUser();
        return simpleChitRepository.findByOwnerIdOrderByCreatedAtDesc(owner.getId());
    }

    @Transactional(readOnly = true)
    public SimpleChitDTO get(Long chitId) {
        return toDTO(requireOwned(chitId));
    }

    /**
     * Update the total amount, commission, per-share amount, escalation settings, and/or
     * individual cells (amount and paid status). Names, shares, and months are fixed.
     */
    @Transactional
    public SimpleChitDTO update(Long chitId, UpdateSimpleChitDTO dto) {
        SimpleChit chit = requireOwned(chitId);

        if (dto.getTotalAmount() != null) {
            chit.setTotalAmount(requirePositive(dto.getTotalAmount(), "Chit amount"));
        }
        if (dto.getCommissionPercent() != null) {
            chit.setCommissionPercent(requireCommission(dto.getCommissionPercent()));
        }
        if (dto.getPerShareAmount() != null) {
            chit.setPerShareAmount(requirePositive(dto.getPerShareAmount(), "Amount per share"));
        }
        if (dto.getEscalationEnabled() != null) {
            chit.setEscalationEnabled(dto.getEscalationEnabled());
        }
        if (dto.getEscalationPercent() != null) {
            chit.setEscalationPercent(requirePercent(dto.getEscalationPercent(), "Escalation percent"));
        }

        if (dto.getEntries() != null && !dto.getEntries().isEmpty()) {
            Map<Long, SimpleChitMember> membersById = membersById(chit);

            for (UpdateSimpleChitDTO.Entry change : dto.getEntries()) {
                SimpleChitMember member = requireMember(membersById, change.getMemberId());
                int month = requireMonth(chit, change.getMonth());

                SimpleChitEntry entry = member.getEntries().stream()
                        .filter(e -> e.getMonthIndex() == month)
                        .findFirst()
                        .orElseGet(() -> {
                            SimpleChitEntry created = new SimpleChitEntry();
                            created.setMember(member);
                            created.setMonthIndex(month);
                            member.getEntries().add(created);
                            return created;
                        });

                if (change.getAmount() != null) {
                    double amount = change.getAmount();
                    if (amount < 0 || Double.isNaN(amount) || Double.isInfinite(amount)) {
                        throw new IllegalArgumentException("Amounts cannot be negative");
                    }
                    entry.setAmount(amount);
                }
                if (change.getPaid() != null && change.getPaid() != entry.isPaid()) {
                    entry.setPaid(change.getPaid());
                    entry.setPaidAt(change.getPaid() ? LocalDateTime.now() : null);
                }
            }
        }

        chit = simpleChitRepository.saveAndFlush(chit);
        return toDTO(chit);
    }

    /**
     * Record (or replace) who received the given month's pot and how much was paid out.
     * When escalation is enabled, the taking member's entries after this month go up by
     * totalAmount * escalationPercent / 100; replacing a payout reverses the old bump first.
     */
    @Transactional
    public SimpleChitDTO savePayout(Long chitId, Integer monthParam, SavePayoutDTO dto) {
        SimpleChit chit = requireOwned(chitId);
        int month = requireMonth(chit, monthParam);
        SimpleChitMember member = requireMember(membersById(chit), dto.getMemberId());
        double amount = requirePositive(dto.getAmount(), "Payout amount");

        SimpleChitPayout payout = chit.getPayouts().stream()
                .filter(p -> p.getMonthIndex() == month)
                .findFirst()
                .orElse(null);

        if (payout != null && payout.getEscalationApplied() != 0) {
            adjustFutureEntries(payout.getMember(), month, -payout.getEscalationApplied());
        }
        if (payout == null) {
            payout = new SimpleChitPayout();
            payout.setChit(chit);
            payout.setMonthIndex(month);
            chit.getPayouts().add(payout);
        }
        payout.setMember(member);
        payout.setAmount(amount);
        payout.setPaidOn(dto.getPaidOn() == null ? LocalDate.now() : dto.getPaidOn());

        double bump = 0;
        if (chit.isEscalationEnabled()) {
            bump = BigDecimal.valueOf(chit.getTotalAmount())
                    .multiply(BigDecimal.valueOf(chit.getEscalationPercent()))
                    .divide(BigDecimal.valueOf(100), 2, RoundingMode.HALF_UP)
                    .doubleValue();
            adjustFutureEntries(member, month, bump);
        }
        payout.setEscalationApplied(bump);

        log.info("Payout recorded for chit {} month {}", chitId, month);
        return toDTO(simpleChitRepository.saveAndFlush(chit));
    }

    @Transactional
    public SimpleChitDTO deletePayout(Long chitId, Integer monthParam) {
        SimpleChit chit = requireOwned(chitId);
        int month = requireMonth(chit, monthParam);
        SimpleChitPayout payout = chit.getPayouts().stream()
                .filter(p -> p.getMonthIndex() == month)
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("No payout recorded for month " + month));

        if (payout.getEscalationApplied() != 0) {
            adjustFutureEntries(payout.getMember(), month, -payout.getEscalationApplied());
        }
        chit.getPayouts().remove(payout);
        return toDTO(simpleChitRepository.saveAndFlush(chit));
    }

    /** Adds {@code delta} (negative to reverse) to a member's entries after {@code afterMonth}. */
    private static void adjustFutureEntries(SimpleChitMember member, int afterMonth, double delta) {
        if (delta == 0) {
            return;
        }
        for (SimpleChitEntry entry : member.getEntries()) {
            if (entry.getMonthIndex() > afterMonth) {
                entry.setAmount(entry.getAmount() + delta);
            }
        }
    }

    @Transactional
    public void delete(Long chitId) {
        SimpleChit chit = requireOwned(chitId);
        // Payouts reference members, so remove them first to keep FK order safe
        chit.getPayouts().clear();
        simpleChitRepository.saveAndFlush(chit);
        simpleChitRepository.delete(chit);
        log.info("Simple chit {} deleted", chitId);
    }

    private SimpleChit requireOwned(Long chitId) {
        User owner = accessControlService.getCurrentUser();
        return simpleChitRepository.findByIdAndOwnerId(chitId, owner.getId())
                .orElseThrow(() -> new AccessDeniedException("Chit not found"));
    }

    private static Map<Long, SimpleChitMember> membersById(SimpleChit chit) {
        return chit.getMembers().stream()
                .collect(Collectors.toMap(SimpleChitMember::getId, Function.identity()));
    }

    private static SimpleChitMember requireMember(Map<Long, SimpleChitMember> membersById, Long memberId) {
        SimpleChitMember member = memberId == null ? null : membersById.get(memberId);
        if (member == null) {
            throw new IllegalArgumentException("Member " + memberId + " is not part of this chit");
        }
        return member;
    }

    private static int requireMonth(SimpleChit chit, Integer monthParam) {
        int month = monthParam == null ? 0 : monthParam;
        if (month < 1 || month > chit.getMonths()) {
            throw new IllegalArgumentException("Month must be between 1 and " + chit.getMonths());
        }
        return month;
    }

    private static String requireName(String value, String label) {
        String trimmed = value == null ? "" : value.trim();
        if (trimmed.isEmpty()) {
            throw new IllegalArgumentException(label + " is required");
        }
        if (trimmed.length() > MAX_NAME_LENGTH) {
            throw new IllegalArgumentException(label + " must be at most " + MAX_NAME_LENGTH + " characters");
        }
        return trimmed;
    }

    private static double requirePositive(Double amount, String label) {
        if (amount == null || amount <= 0 || amount.isNaN() || amount.isInfinite()) {
            throw new IllegalArgumentException(label + " must be greater than 0");
        }
        return amount;
    }

    private static double requireCommission(Double percent) {
        if (percent == null || percent.isNaN() || percent < 0 || percent > MAX_COMMISSION_PERCENT) {
            throw new IllegalArgumentException("Commission must be between 0 and " + (int) MAX_COMMISSION_PERCENT + "%");
        }
        return percent;
    }

    private static double requirePercent(Double percent, String label) {
        if (percent == null || percent.isNaN() || percent < 0 || percent > 100) {
            throw new IllegalArgumentException(label + " must be between 0 and 100");
        }
        return percent;
    }

    private static int requireShares(Integer shares) {
        int value = shares == null ? 1 : shares;
        if (value < 1) {
            throw new IllegalArgumentException("Shares must be at least 1");
        }
        return value;
    }

    private static YearMonth parseStartMonth(String value) {
        if (value == null || value.isBlank()) {
            return YearMonth.now();
        }
        return parseYearMonth(value);
    }

    private static YearMonth parseYearMonth(String value) {
        try {
            return YearMonth.parse(value.trim());
        } catch (DateTimeParseException e) {
            throw new IllegalArgumentException("Start month must be in yyyy-MM format");
        }
    }

    /** Resolves a member's start month to a 1-based month index within [1, months]. */
    private static int resolveStartMonthIndex(YearMonth chitStart, String startMonthStr, int months, YearMonth fallback) {
        YearMonth target = (startMonthStr == null || startMonthStr.isBlank()) ? fallback : parseYearMonth(startMonthStr);
        int index = (int) chitStart.until(target, ChronoUnit.MONTHS) + 1;
        if (index < 1 || index > months) {
            throw new IllegalArgumentException("Start month must fall within the chit's " + months + " months");
        }
        return index;
    }

    private static YearMonth clampToChitRange(YearMonth value, YearMonth chitStart, int months) {
        YearMonth last = chitStart.plusMonths(months - 1L);
        if (value.isBefore(chitStart)) {
            return chitStart;
        }
        if (value.isAfter(last)) {
            return last;
        }
        return value;
    }

    private SimpleChitDTO toDTO(SimpleChit chit) {
        YearMonth chitStart = YearMonth.parse(chit.getStartMonth());
        List<SimpleChitDTO.Member> members = chit.getMembers().stream()
                .map(member -> {
                    Double[] amounts = new Double[chit.getMonths()];
                    Boolean[] paid = new Boolean[chit.getMonths()];
                    Arrays.fill(paid, Boolean.FALSE);
                    for (SimpleChitEntry entry : member.getEntries()) {
                        if (entry.getMonthIndex() >= 1 && entry.getMonthIndex() <= chit.getMonths()) {
                            amounts[entry.getMonthIndex() - 1] = entry.getAmount();
                            paid[entry.getMonthIndex() - 1] = entry.isPaid();
                        }
                    }
                    return SimpleChitDTO.Member.builder()
                            .id(member.getId())
                            .name(member.getName())
                            .shares(member.getShares())
                            .startMonth(chitStart.plusMonths(member.getStartMonthIndex() - 1L).toString())
                            .amounts(Arrays.asList(amounts))
                            .paid(Arrays.asList(paid))
                            .build();
                })
                .toList();

        List<SimpleChitDTO.Payout> payouts = chit.getPayouts().stream()
                .map(p -> SimpleChitDTO.Payout.builder()
                        .month(p.getMonthIndex())
                        .memberId(p.getMember().getId())
                        .memberName(p.getMember().getName())
                        .amount(p.getAmount())
                        .paidOn(p.getPaidOn())
                        .build())
                .toList();

        List<SimpleChitDTO.MonthSummary> monthSummaries = SimpleChitMath.months(chit, YearMonth.now()).stream()
                .map(m -> SimpleChitDTO.MonthSummary.builder()
                        .month(m.month())
                        .calendarMonth(m.calendarMonth().toString())
                        .due(SimpleChitMath.toDouble(m.due()))
                        .collected(SimpleChitMath.toDouble(m.collected()))
                        .pending(SimpleChitMath.toDouble(m.pending()))
                        .payout(SimpleChitMath.toDouble(m.payout()))
                        .pnl(SimpleChitMath.toDouble(m.pnl()))
                        .isDue(m.isDue())
                        .build())
                .toList();

        return SimpleChitDTO.builder()
                .id(chit.getId())
                .name(chit.getName())
                .totalAmount(chit.getTotalAmount())
                .months(chit.getMonths())
                .startMonth(chit.getStartMonth())
                .commissionPercent(chit.getCommissionPercent())
                .perShareAmount(chit.getPerShareAmount())
                .escalationEnabled(chit.isEscalationEnabled())
                .escalationPercent(chit.getEscalationPercent())
                .members(members)
                .payouts(payouts)
                .monthSummaries(monthSummaries)
                .createdAt(chit.getCreatedAt())
                .updatedAt(chit.getUpdatedAt())
                .build();
    }
}
