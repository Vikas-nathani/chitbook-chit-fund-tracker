package com.nival.chit.services;

import com.nival.chit.dto.AddSimpleChitMemberDTO;
import com.nival.chit.dto.CreateSimpleChitDTO;
import com.nival.chit.dto.SavePayoutDTO;
import com.nival.chit.dto.SimpleChitDTO;
import com.nival.chit.entity.SimpleChit;
import com.nival.chit.entity.User;
import com.nival.chit.enums.UserRoles;
import com.nival.chit.repository.SimpleChitRepository;
import com.nival.chit.security.AccessControlService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class SimpleChitServiceTest {

    @Mock
    private SimpleChitRepository simpleChitRepository;

    @Mock
    private AccessControlService accessControlService;

    private SimpleChitService service;
    private User owner;
    private SimpleChit lastSavedChit;

    @BeforeEach
    void setUp() {
        service = new SimpleChitService(simpleChitRepository, accessControlService);

        owner = new User();
        owner.setId(1L);
        owner.setUsername("vikas");
        owner.setRole(UserRoles.ADMIN);

        lenient().when(accessControlService.getCurrentUser()).thenReturn(owner);
        lenient().when(simpleChitRepository.save(any(SimpleChit.class))).thenAnswer(inv -> {
            lastSavedChit = inv.getArgument(0);
            return lastSavedChit;
        });
        lenient().when(simpleChitRepository.saveAndFlush(any(SimpleChit.class))).thenAnswer(inv -> inv.getArgument(0));
    }

    private CreateSimpleChitDTO.MemberInput member(String name, Integer shares, String startMonth) {
        return new CreateSimpleChitDTO.MemberInput(name, shares, startMonth);
    }

    @Test
    void createAppliesSharesMultiplierAndDefaultPerShareAmount() {
        CreateSimpleChitDTO dto = new CreateSimpleChitDTO();
        dto.setName("Family chit");
        dto.setTotalAmount(500000.0);
        dto.setMonths(20);
        dto.setStartMonth("2026-08");
        dto.setMembers(List.of(
                member("Ramesh", 2, null),
                member("Priya", null, null)
        ));

        SimpleChitDTO result = service.create(dto);

        assertThat(result.getPerShareAmount()).isEqualTo(25000.0);

        SimpleChitDTO.Member ramesh = result.getMembers().get(0);
        assertThat(ramesh.getShares()).isEqualTo(2);
        assertThat(ramesh.getStartMonth()).isEqualTo("2026-08");
        assertThat(ramesh.getAmounts().get(0)).isEqualTo(50000.0);
        assertThat(ramesh.getAmounts().get(19)).isEqualTo(50000.0);

        SimpleChitDTO.Member priya = result.getMembers().get(1);
        assertThat(priya.getShares()).isEqualTo(1);
        assertThat(priya.getAmounts().get(0)).isEqualTo(25000.0);
    }

    @Test
    void createLeavesEntriesEmptyBeforeMembersStartMonth() {
        CreateSimpleChitDTO dto = new CreateSimpleChitDTO();
        dto.setName("Staggered chit");
        dto.setTotalAmount(250000.0);
        dto.setMonths(10);
        dto.setStartMonth("2026-08");
        dto.setMembers(List.of(member("LateJoiner", 1, "2026-11")));

        SimpleChitDTO result = service.create(dto);

        SimpleChitDTO.Member lateJoiner = result.getMembers().get(0);
        assertThat(lateJoiner.getStartMonth()).isEqualTo("2026-11");
        // months 1-3 (Aug, Sep, Oct) have no entry -> null
        assertThat(lateJoiner.getAmounts().get(0)).isNull();
        assertThat(lateJoiner.getAmounts().get(1)).isNull();
        assertThat(lateJoiner.getAmounts().get(2)).isNull();
        // month 4 (Nov) onward has an entry
        assertThat(lateJoiner.getAmounts().get(3)).isEqualTo(25000.0);
        assertThat(lateJoiner.getAmounts().get(9)).isEqualTo(25000.0);
    }

    @Test
    void addMemberStartsAtGivenMonthWithoutTouchingOtherMembers() {
        SimpleChit chit = baseChit();
        when(simpleChitRepository.findByIdAndOwnerId(1L, 1L)).thenReturn(Optional.of(chit));

        AddSimpleChitMemberDTO dto = new AddSimpleChitMemberDTO("NewPerson", 1, "2026-11");
        SimpleChitDTO result = service.addMember(1L, dto);

        // baseChit() already has Ramesh + Priya; adding NewPerson makes 3
        assertThat(result.getMembers()).hasSize(3);
        SimpleChitDTO.Member added = result.getMembers().get(2);
        assertThat(added.getName()).isEqualTo("NewPerson");
        assertThat(added.getStartMonth()).isEqualTo("2026-11");
        assertThat(added.getAmounts().get(0)).isNull();
        assertThat(added.getAmounts().get(3)).isEqualTo(25000.0);

        // original member (Ramesh, shares=2) untouched
        SimpleChitDTO.Member original = result.getMembers().get(0);
        assertThat(original.getAmounts().get(0)).isEqualTo(50000.0);
    }

    @Test
    void addMemberRejectsNonOwner() {
        when(simpleChitRepository.findByIdAndOwnerId(1L, 1L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.addMember(1L, new AddSimpleChitMemberDTO("X", 1, null)))
                .isInstanceOf(AccessDeniedException.class);
    }

    @Test
    void savePayoutWithEscalationBumpsOnlyThatMembersFutureMonths() {
        SimpleChit chit = baseChit();
        chit.setEscalationEnabled(true);
        chit.setEscalationPercent(1.0);
        when(simpleChitRepository.findByIdAndOwnerId(1L, 1L)).thenReturn(Optional.of(chit));

        Long rameshId = chit.getMembers().get(0).getId();
        SavePayoutDTO payoutDTO = new SavePayoutDTO(rameshId, 500000.0, LocalDate.of(2026, 12, 1));
        SimpleChitDTO result = service.savePayout(1L, 5, payoutDTO);

        SimpleChitDTO.Member ramesh = result.getMembers().get(0);
        // Ramesh has shares=2 -> base 50,000/month; months 1-5 unaffected,
        // months 6-20 bumped by 500000 * 1% = 5000 -> 55,000
        assertThat(ramesh.getAmounts().get(3)).isEqualTo(50000.0);
        assertThat(ramesh.getAmounts().get(4)).isEqualTo(50000.0);
        assertThat(ramesh.getAmounts().get(5)).isEqualTo(55000.0);
        assertThat(ramesh.getAmounts().get(19)).isEqualTo(55000.0);
    }

    @Test
    void deletePayoutReversesEscalationExactly() {
        SimpleChit chit = baseChit();
        chit.setEscalationEnabled(true);
        chit.setEscalationPercent(1.0);
        when(simpleChitRepository.findByIdAndOwnerId(1L, 1L)).thenReturn(Optional.of(chit));

        Long rameshId = chit.getMembers().get(0).getId();
        service.savePayout(1L, 5, new SavePayoutDTO(rameshId, 500000.0, LocalDate.of(2026, 12, 1)));

        SimpleChitDTO afterDelete = service.deletePayout(1L, 5);

        SimpleChitDTO.Member ramesh = afterDelete.getMembers().get(0);
        assertThat(ramesh.getAmounts().get(5)).isEqualTo(50000.0);
        assertThat(ramesh.getAmounts().get(19)).isEqualTo(50000.0);
    }

    @Test
    void replacingPayoutReversesOldEscalationBeforeApplyingNew() {
        SimpleChit chit = baseChit();
        chit.setEscalationEnabled(true);
        chit.setEscalationPercent(1.0);
        when(simpleChitRepository.findByIdAndOwnerId(1L, 1L)).thenReturn(Optional.of(chit));

        Long rameshId = chit.getMembers().get(0).getId();
        Long priyaId = chit.getMembers().get(1).getId();

        service.savePayout(1L, 5, new SavePayoutDTO(rameshId, 500000.0, LocalDate.of(2026, 12, 1)));
        // replace month 5's payout with a different member
        SimpleChitDTO result = service.savePayout(1L, 5, new SavePayoutDTO(priyaId, 500000.0, LocalDate.of(2026, 12, 2)));

        SimpleChitDTO.Member ramesh = result.getMembers().get(0);
        SimpleChitDTO.Member priya = result.getMembers().get(1);
        // Ramesh's bump reversed back to his base 50,000 (shares=2)
        assertThat(ramesh.getAmounts().get(5)).isEqualTo(50000.0);
        // Priya (shares=1, base 25,000) now has the bump applied once (not doubled)
        assertThat(priya.getAmounts().get(5)).isEqualTo(30000.0);
    }

    private SimpleChit baseChit() {
        CreateSimpleChitDTO dto = new CreateSimpleChitDTO();
        dto.setName("Family chit");
        dto.setTotalAmount(500000.0);
        dto.setMonths(20);
        dto.setStartMonth("2026-08");
        dto.setMembers(List.of(member("Ramesh", 2, null), member("Priya", 1, null)));
        service.create(dto);
        // save() never assigns real identity-generated ids in this unit test, so assign distinct
        // ones manually (SimpleChitMember.id has no public setter by design).
        for (int i = 0; i < lastSavedChit.getMembers().size(); i++) {
            ReflectionTestUtils.setField(lastSavedChit.getMembers().get(i), "id", (long) (i + 1));
        }
        return lastSavedChit;
    }
}
