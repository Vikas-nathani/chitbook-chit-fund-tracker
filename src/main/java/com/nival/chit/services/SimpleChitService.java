package com.nival.chit.services;

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

    private final SimpleChitRepository simpleChitRepository;
    private final AccessControlService accessControlService;

    /**
     * Create a chit and prefill every cell (as pending) with {@code totalAmount / memberCount}.
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
        List<String> memberNames = dto.getMemberNames() == null ? List.of() : dto.getMemberNames().stream()
                .map(n -> n == null ? "" : n.trim())
                .filter(n -> !n.isEmpty())
                .toList();
        if (memberNames.isEmpty() || memberNames.size() > MAX_MEMBERS) {
            throw new IllegalArgumentException("Add between 1 and " + MAX_MEMBERS + " member names");
        }
        memberNames.forEach(n -> requireName(n, "Member name"));

        double installment = BigDecimal.valueOf(totalAmount)
                .divide(BigDecimal.valueOf(memberNames.size()), 2, RoundingMode.HALF_UP)
                .doubleValue();

        SimpleChit chit = new SimpleChit();
        chit.setName(name);
        chit.setTotalAmount(totalAmount);
        chit.setMonths(months);
        chit.setStartMonth(parseStartMonth(dto.getStartMonth()).toString());
        chit.setCommissionPercent(dto.getCommissionPercent() == null
                ? DEFAULT_COMMISSION_PERCENT
                : requireCommission(dto.getCommissionPercent()));
        chit.setOwner(owner);

        for (int i = 0; i < memberNames.size(); i++) {
            SimpleChitMember member = new SimpleChitMember();
            member.setChit(chit);
            member.setName(memberNames.get(i));
            member.setPosition(i);
            for (int month = 1; month <= months; month++) {
                SimpleChitEntry entry = new SimpleChitEntry();
                entry.setMember(member);
                entry.setMonthIndex(month);
                entry.setAmount(installment);
                member.getEntries().add(entry);
            }
            chit.getMembers().add(member);
        }

        chit = simpleChitRepository.save(chit);
        log.info("Simple chit {} created by {}", chit.getId(), owner.getUsername());
        return toDTO(chit);
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
     * Update the total amount, commission, and/or individual cells (amount and paid status).
     * Names and months are fixed.
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
                .orElseGet(() -> {
                    SimpleChitPayout created = new SimpleChitPayout();
                    created.setChit(chit);
                    created.setMonthIndex(month);
                    chit.getPayouts().add(created);
                    return created;
                });
        payout.setMember(member);
        payout.setAmount(amount);
        payout.setPaidOn(dto.getPaidOn() == null ? LocalDate.now() : dto.getPaidOn());

        log.info("Payout recorded for chit {} month {}", chitId, month);
        return toDTO(simpleChitRepository.saveAndFlush(chit));
    }

    @Transactional
    public SimpleChitDTO deletePayout(Long chitId, Integer monthParam) {
        SimpleChit chit = requireOwned(chitId);
        int month = requireMonth(chit, monthParam);
        boolean removed = chit.getPayouts().removeIf(p -> p.getMonthIndex() == month);
        if (!removed) {
            throw new IllegalArgumentException("No payout recorded for month " + month);
        }
        return toDTO(simpleChitRepository.saveAndFlush(chit));
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

    private static YearMonth parseStartMonth(String value) {
        if (value == null || value.isBlank()) {
            return YearMonth.now();
        }
        try {
            return YearMonth.parse(value.trim());
        } catch (DateTimeParseException e) {
            throw new IllegalArgumentException("Start month must be in yyyy-MM format");
        }
    }

    private SimpleChitDTO toDTO(SimpleChit chit) {
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
                .members(members)
                .payouts(payouts)
                .monthSummaries(monthSummaries)
                .createdAt(chit.getCreatedAt())
                .updatedAt(chit.getUpdatedAt())
                .build();
    }
}
