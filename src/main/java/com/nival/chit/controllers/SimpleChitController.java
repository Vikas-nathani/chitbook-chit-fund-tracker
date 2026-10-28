package com.nival.chit.controllers;

import com.nival.chit.dto.AddSimpleChitMemberDTO;
import com.nival.chit.dto.CreateSimpleChitDTO;
import com.nival.chit.dto.SavePayoutDTO;
import com.nival.chit.dto.SimpleChitDTO;
import com.nival.chit.dto.SimpleChitStatsDTO;
import com.nival.chit.dto.SimpleChitSummaryDTO;
import com.nival.chit.dto.UpdateSimpleChitDTO;
import com.nival.chit.services.SimpleChitService;
import com.nival.chit.services.SimpleChitStatsService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * REST controller for simple chits: a member-name x month grid of amounts,
 * visible only to the user who created it.
 */
@RestController
@RequestMapping("/api/chit/simple-chits")
@RequiredArgsConstructor
@Tag(name = "Simple Chits", description = "Create chits with member names and months, and edit monthly amounts.")
public class SimpleChitController {

    private final SimpleChitService simpleChitService;
    private final SimpleChitStatsService simpleChitStatsService;

    @GetMapping
    @Operation(summary = "List my chits", description = "Returns the chits created by the current user, newest first.")
    public ResponseEntity<List<SimpleChitSummaryDTO>> listMine() {
        return ResponseEntity.ok(simpleChitService.listMine());
    }

    @GetMapping("/stats")
    @Operation(
        summary = "Owner stats",
        description = "Totals, monthly P/L and collections, per-chit health, and pending dues across my chits."
    )
    public ResponseEntity<SimpleChitStatsDTO> stats() {
        return ResponseEntity.ok(simpleChitStatsService.statsForCurrentUser());
    }

    @PostMapping
    @Operation(
        summary = "Create a chit",
        description = "Creates a chit and prefills every month for every member with total amount / member count."
    )
    @ApiResponses(value = {
        @ApiResponse(
            responseCode = "201",
            description = "Chit created",
            content = @Content(schema = @Schema(implementation = SimpleChitDTO.class))
        ),
        @ApiResponse(responseCode = "400", description = "Invalid input data")
    })
    public ResponseEntity<SimpleChitDTO> create(@RequestBody CreateSimpleChitDTO createDTO) {
        return ResponseEntity.status(HttpStatus.CREATED).body(simpleChitService.create(createDTO));
    }

    @PostMapping("/{chitId}/members")
    @Operation(
        summary = "Add a member",
        description = "Adds a new member to an existing chit. Their entries start at their own start month " +
                     "(default: the current month) and run through the chit's last month."
    )
    public ResponseEntity<SimpleChitDTO> addMember(@PathVariable Long chitId, @RequestBody AddSimpleChitMemberDTO memberDTO) {
        return ResponseEntity.ok(simpleChitService.addMember(chitId, memberDTO));
    }

    @PutMapping("/{chitId}/payouts/{month}")
    @Operation(
        summary = "Record payout",
        description = "Records (or replaces) which member received the given month's pot and the amount paid out."
    )
    public ResponseEntity<SimpleChitDTO> savePayout(
            @PathVariable Long chitId,
            @PathVariable Integer month,
            @RequestBody SavePayoutDTO payoutDTO) {
        return ResponseEntity.ok(simpleChitService.savePayout(chitId, month, payoutDTO));
    }

    @DeleteMapping("/{chitId}/payouts/{month}")
    @Operation(summary = "Remove payout", description = "Removes the payout recorded for the given month.")
    public ResponseEntity<SimpleChitDTO> deletePayout(@PathVariable Long chitId, @PathVariable Integer month) {
        return ResponseEntity.ok(simpleChitService.deletePayout(chitId, month));
    }

    @GetMapping("/{chitId:\\d+}")
    @Operation(summary = "Get chit grid", description = "Returns the full member x month grid of one of my chits.")
    public ResponseEntity<SimpleChitDTO> get(@PathVariable Long chitId) {
        return ResponseEntity.ok(simpleChitService.get(chitId));
    }

    @PutMapping("/{chitId}")
    @Operation(
        summary = "Update amounts",
        description = "Updates the total chit amount and/or individual cell amounts. Names and months cannot change."
    )
    public ResponseEntity<SimpleChitDTO> update(@PathVariable Long chitId, @RequestBody UpdateSimpleChitDTO updateDTO) {
        return ResponseEntity.ok(simpleChitService.update(chitId, updateDTO));
    }

    @DeleteMapping("/{chitId}")
    @Operation(summary = "Delete a chit", description = "Permanently deletes one of my chits.")
    public ResponseEntity<Void> delete(@PathVariable Long chitId) {
        simpleChitService.delete(chitId);
        return ResponseEntity.noContent().build();
    }
}
