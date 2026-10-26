package com.nival.chit.services;

import com.nival.chit.dto.SimpleChitSummaryDTO;
import com.nival.chit.entity.SimpleChit;
import com.nival.chit.entity.SimpleChitEntry;
import com.nival.chit.entity.SimpleChitMember;
import com.nival.chit.entity.SimpleChitPayout;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.YearMonth;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * Single source of the simple-chit money rules, shared by the chit view and the stats.
 *
 * <ul>
 *     <li>Due(m) = sum of cell amounts; Collected(m) = sum of paid cells; Pending(m) = Due - Collected</li>
 *     <li>A month is due once its calendar month is on or before the current month; overdue when before it</li>
 *     <li>P/L(m) = Collected(m) - Payout(m), only for months with a recorded payout</li>
 * </ul>
 */
final class SimpleChitMath {

    private SimpleChitMath() {
    }

    /** Money figures for one month of one chit. {@code payout}/{@code pnl} are null without a payout. */
    record MonthCalc(
            int month,
            YearMonth calendarMonth,
            BigDecimal due,
            BigDecimal collected,
            BigDecimal pending,
            BigDecimal payout,
            BigDecimal pnl,
            boolean isDue,
            boolean isOverdue
    ) {
    }

    static YearMonth startOf(SimpleChit chit) {
        return YearMonth.parse(chit.getStartMonth());
    }

    static List<MonthCalc> months(SimpleChit chit, YearMonth now) {
        YearMonth start = startOf(chit);
        Map<Integer, SimpleChitPayout> payoutsByMonth = chit.getPayouts().stream()
                .collect(Collectors.toMap(SimpleChitPayout::getMonthIndex, Function.identity(), (a, b) -> a));

        BigDecimal[] due = new BigDecimal[chit.getMonths()];
        BigDecimal[] collected = new BigDecimal[chit.getMonths()];
        for (int i = 0; i < chit.getMonths(); i++) {
            due[i] = BigDecimal.ZERO;
            collected[i] = BigDecimal.ZERO;
        }
        for (SimpleChitMember member : chit.getMembers()) {
            for (SimpleChitEntry entry : member.getEntries()) {
                int i = entry.getMonthIndex() - 1;
                if (i < 0 || i >= chit.getMonths()) {
                    continue;
                }
                BigDecimal amount = money(entry.getAmount());
                due[i] = due[i].add(amount);
                if (entry.isPaid()) {
                    collected[i] = collected[i].add(amount);
                }
            }
        }

        List<MonthCalc> result = new ArrayList<>(chit.getMonths());
        for (int i = 0; i < chit.getMonths(); i++) {
            int month = i + 1;
            YearMonth calendar = start.plusMonths(i);
            SimpleChitPayout payout = payoutsByMonth.get(month);
            BigDecimal payoutAmount = payout == null ? null : money(payout.getAmount());
            result.add(new MonthCalc(
                    month,
                    calendar,
                    due[i],
                    collected[i],
                    due[i].subtract(collected[i]).max(BigDecimal.ZERO),
                    payoutAmount,
                    payoutAmount == null ? null : collected[i].subtract(payoutAmount),
                    !calendar.isAfter(now),
                    calendar.isBefore(now)
            ));
        }
        return result;
    }

    static SimpleChitSummaryDTO summary(SimpleChit chit, YearMonth now) {
        List<MonthCalc> months = months(chit, now);
        BigDecimal dueToDate = BigDecimal.ZERO;
        BigDecimal collected = BigDecimal.ZERO;
        BigDecimal pending = BigDecimal.ZERO;
        BigDecimal overdue = BigDecimal.ZERO;
        BigDecimal paidOut = BigDecimal.ZERO;
        BigDecimal profit = BigDecimal.ZERO;
        int elapsed = 0;
        int payoutsDone = 0;

        for (MonthCalc m : months) {
            // Paid cells count as collected even when paid ahead of their month
            collected = collected.add(m.collected());
            if (m.isDue()) {
                elapsed++;
                dueToDate = dueToDate.add(m.due());
                pending = pending.add(m.pending());
            }
            if (m.isOverdue()) {
                overdue = overdue.add(m.pending());
            }
            if (m.payout() != null) {
                payoutsDone++;
                paidOut = paidOut.add(m.payout());
                profit = profit.add(m.pnl());
            }
        }

        return SimpleChitSummaryDTO.builder()
                .id(chit.getId())
                .name(chit.getName())
                .totalAmount(chit.getTotalAmount())
                .months(chit.getMonths())
                .startMonth(chit.getStartMonth())
                .memberCount(chit.getMembers().size())
                .commissionPercent(chit.getCommissionPercent())
                .monthsElapsed(elapsed)
                .dueToDate(toDouble(dueToDate))
                .collected(toDouble(collected))
                .pending(toDouble(pending))
                .overdue(toDouble(overdue))
                .payoutsDone(payoutsDone)
                .paidOut(toDouble(paidOut))
                .profit(toDouble(profit))
                .createdAt(chit.getCreatedAt())
                .build();
    }

    static BigDecimal money(double value) {
        return BigDecimal.valueOf(value).setScale(2, RoundingMode.HALF_UP);
    }

    static Double toDouble(BigDecimal value) {
        return value == null ? null : value.setScale(2, RoundingMode.HALF_UP).doubleValue();
    }
}
