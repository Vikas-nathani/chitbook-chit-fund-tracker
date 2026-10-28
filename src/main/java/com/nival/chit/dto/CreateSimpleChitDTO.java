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
    /** Optional. Defaults to totalAmount / months. The one common monthly slot amount for every member. */
    private Double perShareAmount;
    private List<MemberInput> members;
    /** Optional owner commission percent (0-20). Defaults to 5. */
    private Double commissionPercent;
    /** Optional. Defaults to false. */
    private Boolean escalationEnabled;
    /** Optional. Defaults to 1 when escalationEnabled is true. */
    private Double escalationPercent;

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class MemberInput {
        private String name;
        /** Optional, defaults to 1. How many chit slots this member holds. */
        private Integer shares;
        /** Optional, {@code yyyy-MM}. Defaults to the chit's own startMonth. */
        private String startMonth;
    }
}
