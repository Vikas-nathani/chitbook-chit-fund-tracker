package com.nival.chit.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * Request payload for creating a simple chit.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class CreateSimpleChitDTO {
    private String name;
    private Double totalAmount;
    private Integer months;
    /** Optional, {@code yyyy-MM}. Defaults to the current month. */
    private String startMonth;
    private List<String> memberNames;
    /** Optional owner commission percent (0-20). Defaults to 5. */
    private Double commissionPercent;
}
