package com.nival.chit.services;

import com.nival.chit.dto.SimpleChitStatsDTO;
import com.nival.chit.dto.SimpleChitSummaryDTO;
import com.nival.chit.entity.SimpleChit;
import com.nival.chit.entity.SimpleChitEntry;
import com.nival.chit.entity.SimpleChitMember;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.YearMonth;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * Owner-level stats across the current user's simple chits. Uses {@link SimpleChitMath}
 * so the numbers match the per-chit view exactly. Scope comes from
 * {@link SimpleChitService#findMine()} (owner-only).
 */
@Service
@RequiredArgsConstructor
public class SimpleChitStatsService {

    /** Max calendar months returned in the monthly series. */
    private static final int MAX_SERIES_MONTHS = 18;
    /** Months after the current one still shown in the series. */
    private static final int FUTURE_MONTHS = 2;

    private final SimpleChitService simpleChitService;

    @Transactional(readOnly = true)
    public SimpleChitStatsDTO statsForCurrentUser() {
        YearMonth now = YearMonth.now();
        LocalDate today = LocalDate.now();
        List<SimpleChit> chits = simpleChitService.findMine();

        List<SimpleChitSummaryDTO> perChit = new ArrayList<>();
        Map<YearMonth, BigDecimal[]> monthly = new TreeMap<>(); // due, collected, payout, pnl
        List<SimpleChitStatsDTO.PendingDue> pendingDues = new ArrayList<>();
        BigDecimal expectedCommission = BigDecimal.ZERO;

        for (SimpleChit chit : chits) {
            perChit.add(SimpleChitMath.summary(chit, now));
            expectedCommission = expectedCommission.add(BigDecimal.valueOf(chit.getTotalAmount())
                    .multiply(BigDecimal.valueOf(chit.getCommissionPercent()))
                    .divide(BigDecimal.valueOf(100), 2, RoundingMode.HALF_UP)
                    .multiply(BigDecimal.valueOf(chit.getMonths())));

            for (SimpleChitMath.MonthCalc m : SimpleChitMath.months(chit, now)) {
                BigDecimal[] point = monthly.computeIfAbsent(m.calendarMonth(),
                        k -> new BigDecimal[]{BigDecimal.ZERO, BigDecimal.ZERO, BigDecimal.ZERO, BigDecimal.ZERO});
                point[0] = point[0].add(m.due());
                point[1] = point[1].add(m.collected());
                if (m.payout() != null) {
                    point[2] = point[2].add(m.payout());
                    point[3] = point[3].add(m.pnl());
                }
            }

            YearMonth start = SimpleChitMath.startOf(chit);
            for (SimpleChitMember member : chit.getMembers()) {
                for (SimpleChitEntry entry : member.getEntries()) {
                    YearMonth calendar = start.plusMonths(entry.getMonthIndex() - 1L);
                    if (entry.isPaid() || entry.getAmount() <= 0 || calendar.isAfter(now)) {
                        continue;
                    }
                    boolean overdue = calendar.isBefore(now);
                    // Overdue counts from the first day of the following month
                    long days = overdue ? ChronoUnit.DAYS.between(calendar.plusMonths(1).atDay(1), today) : 0;
                    pendingDues.add(SimpleChitStatsDTO.PendingDue.builder()
                            .chitId(chit.getId())
                            .chitName(chit.getName())
                            .memberId(member.getId())
                            .memberName(member.getName())
                            .month(entry.getMonthIndex())
                            .calendarMonth(calendar.toString())
                            .amount(SimpleChitMath.toDouble(SimpleChitMath.money(entry.getAmount())))
                            .overdue(overdue)
                            .daysOverdue(Math.max(days, 0))
                            .build());
                }
            }
        }

        pendingDues.sort(Comparator
                .comparing(SimpleChitStatsDTO.PendingDue::getCalendarMonth)
                .thenComparing(SimpleChitStatsDTO.PendingDue::getChitName)
                .thenComparing(SimpleChitStatsDTO.PendingDue::getMemberName));

        return SimpleChitStatsDTO.builder()
                .totals(totals(perChit, expectedCommission))
                .monthly(series(monthly, now))
                .perChit(perChit)
                .pendingDues(pendingDues)
                .build();
    }

    private static SimpleChitStatsDTO.Totals totals(List<SimpleChitSummaryDTO> perChit, BigDecimal expectedCommission) {
        BigDecimal due = sum(perChit, SimpleChitSummaryDTO::getDueToDate);
        BigDecimal collected = sum(perChit, SimpleChitSummaryDTO::getCollected);
        BigDecimal paidOut = sum(perChit, SimpleChitSummaryDTO::getPaidOut);
        return SimpleChitStatsDTO.Totals.builder()
                .chits(perChit.size())
                .dueToDate(SimpleChitMath.toDouble(due))
                .collected(SimpleChitMath.toDouble(collected))
                .pending(SimpleChitMath.toDouble(sum(perChit, SimpleChitSummaryDTO::getPending)))
                .overdue(SimpleChitMath.toDouble(sum(perChit, SimpleChitSummaryDTO::getOverdue)))
                .paidOut(SimpleChitMath.toDouble(paidOut))
                .cashInHand(SimpleChitMath.toDouble(collected.subtract(paidOut)))
                .profit(SimpleChitMath.toDouble(sum(perChit, SimpleChitSummaryDTO::getProfit)))
                .expectedCommission(SimpleChitMath.toDouble(expectedCommission))
                .collectionRate(due.signum() == 0 ? null
                        : collected.min(due).divide(due, 4, RoundingMode.HALF_UP).doubleValue())
                .build();
    }

    /** Calendar months from the earliest start up to current + {@link #FUTURE_MONTHS}, last N only. */
    private static List<SimpleChitStatsDTO.MonthPoint> series(Map<YearMonth, BigDecimal[]> monthly, YearMonth now) {
        List<SimpleChitStatsDTO.MonthPoint> points = new ArrayList<>();
        if (monthly.isEmpty()) {
            return points;
        }
        YearMonth first = ((TreeMap<YearMonth, BigDecimal[]>) monthly).firstKey();
        YearMonth last = ((TreeMap<YearMonth, BigDecimal[]>) monthly).lastKey();
        YearMonth end = last.isBefore(now.plusMonths(FUTURE_MONTHS)) ? last : now.plusMonths(FUTURE_MONTHS);

        BigDecimal cumulative = BigDecimal.ZERO;
        for (YearMonth ym = first; !ym.isAfter(end); ym = ym.plusMonths(1)) {
            BigDecimal[] p = monthly.getOrDefault(ym,
                    new BigDecimal[]{BigDecimal.ZERO, BigDecimal.ZERO, BigDecimal.ZERO, BigDecimal.ZERO});
            cumulative = cumulative.add(p[3]);
            points.add(SimpleChitStatsDTO.MonthPoint.builder()
                    .month(ym.toString())
                    .due(SimpleChitMath.toDouble(p[0]))
                    .collected(SimpleChitMath.toDouble(p[1]))
                    .payout(SimpleChitMath.toDouble(p[2]))
                    .pnl(SimpleChitMath.toDouble(p[3]))
                    .cumulativePnl(SimpleChitMath.toDouble(cumulative))
                    .build());
        }
        // Cumulative is computed over the full range first, so trimming keeps correct running totals
        return points.size() > MAX_SERIES_MONTHS
                ? new ArrayList<>(points.subList(points.size() - MAX_SERIES_MONTHS, points.size()))
                : points;
    }

    private static BigDecimal sum(List<SimpleChitSummaryDTO> rows, java.util.function.Function<SimpleChitSummaryDTO, Double> field) {
        return rows.stream()
                .map(field)
                .map(v -> v == null ? BigDecimal.ZERO : BigDecimal.valueOf(v))
                .reduce(BigDecimal.ZERO, BigDecimal::add);
    }
}
