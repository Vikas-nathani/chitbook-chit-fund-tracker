package com.nival.chit.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

/**
 * Full member x month grid of a simple chit, with payouts and per-month P/L.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SimpleChitDTO {
    private Long id;
    private String name;
    private Double totalAmount;
    private Integer months;
    private String startMonth;
    private Double commissionPercent;
    private List<Member> members;
    private List<Payout> payouts;
    /** Computed money summary for each month, index i = month i + 1. */
    private List<MonthSummary> monthSummaries;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    /**
     * One grid row. {@code amounts.get(i)} / {@code paid.get(i)} are for month {@code i + 1}.
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Member {
        private Long id;
        private String name;
        private List<Double> amounts;
        private List<Boolean> paid;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Payout {
        private Integer month;
        private Long memberId;
        private String memberName;
        private Double amount;
        private LocalDate paidOn;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class MonthSummary {
        private Integer month;
        /** Calendar month, {@code yyyy-MM}. */
        private String calendarMonth;
        private Double due;
        private Double collected;
        private Double pending;
        /** Null when no payout is recorded for the month. */
        private Double payout;
        /** Collected minus payout; null until a payout is recorded. */
        private Double pnl;
        /** Calendar month is on or before the current month. */
        private Boolean isDue;
    }
}
