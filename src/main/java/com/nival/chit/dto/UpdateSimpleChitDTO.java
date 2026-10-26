package com.nival.chit.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * Amount/status update for a simple chit. Names and months cannot change.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class UpdateSimpleChitDTO {
    /** Optional new total chit amount. Existing cell amounts are not recomputed. */
    private Double totalAmount;
    /** Optional new owner commission percent (0-20). */
    private Double commissionPercent;
    /** Optional cell changes. */
    private List<Entry> entries;

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Entry {
        private Long memberId;
        /** 1-based month number. */
        private Integer month;
        /** Optional new amount; unchanged when null. */
        private Double amount;
        /** Optional paid status; unchanged when null. */
        private Boolean paid;
    }
}
