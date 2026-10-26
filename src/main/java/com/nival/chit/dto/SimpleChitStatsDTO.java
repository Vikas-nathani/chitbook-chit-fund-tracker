package com.nival.chit.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * Owner-level stats across all of the current user's simple chits.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SimpleChitStatsDTO {
    private Totals totals;
    private List<MonthPoint> monthly;
    private List<SimpleChitSummaryDTO> perChit;
    private List<PendingDue> pendingDues;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Totals {
        private Integer chits;
        private Double dueToDate;
        private Double collected;
        private Double pending;
        private Double overdue;
        private Double paidOut;
        /** Collected minus paid out. */
        private Double cashInHand;
        private Double profit;
        /** Commission percent x chit amount x months, summed over chits. */
        private Double expectedCommission;
        /** Collected / due to date, 0..1 (null when nothing is due yet). */
        private Double collectionRate;
    }

    /** Totals for one calendar month across all chits. */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class MonthPoint {
        /** {@code yyyy-MM}. */
        private String month;
        private Double due;
        private Double collected;
        private Double payout;
        private Double pnl;
        private Double cumulativePnl;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PendingDue {
        private Long chitId;
        private String chitName;
        private Long memberId;
        private String memberName;
        private Integer month;
        /** {@code yyyy-MM}. */
        private String calendarMonth;
        private Double amount;
        private Boolean overdue;
        /** Days since the start of the month after the due month; 0 when not overdue. */
        private Long daysOverdue;
    }
}
