package com.nival.chit.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * List view of a simple chit with its money position.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SimpleChitSummaryDTO {
    private Long id;
    private String name;
    private Double totalAmount;
    private Integer months;
    private String startMonth;
    private Integer memberCount;
    private Double commissionPercent;
    /** Months whose calendar month has started (0..months). */
    private Integer monthsElapsed;
    /** Sum of cell amounts in months that are due so far. */
    private Double dueToDate;
    /** Sum of cells marked paid. */
    private Double collected;
    /** Unpaid amount in months that are due so far. */
    private Double pending;
    /** Unpaid amount in months before the current month. */
    private Double overdue;
    private Integer payoutsDone;
    private Double paidOut;
    /** Realised owner profit: collected minus payout, over months with a payout. */
    private Double profit;
    private LocalDateTime createdAt;
}
