package com.nival.chit.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;

/**
 * Records who received a month's pot and how much was paid out.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class SavePayoutDTO {
    private Long memberId;
    private Double amount;
    /** Optional; defaults to today. */
    private LocalDate paidOn;
}
