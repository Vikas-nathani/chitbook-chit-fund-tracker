package com.nival.chit.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Request payload for adding a member to an existing simple chit after creation.
 * Amount is derived from the chit's own {@code perShareAmount}, not supplied here.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class AddSimpleChitMemberDTO {
    private String name;
    /** Optional, defaults to 1. How many chit slots this member holds. */
    private Integer shares;
    /** Optional, {@code yyyy-MM}. Defaults to the current calendar month (clamped to the chit's range). */
    private String startMonth;
}
