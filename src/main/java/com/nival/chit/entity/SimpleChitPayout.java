package com.nival.chit.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.ColumnDefault;

import java.time.LocalDate;

/**
 * The pot paid out to one member for one month of a {@link SimpleChit}.
 * Owner P/L for the month is collected cells minus this amount.
 */
@Entity
@Getter
@Setter
@Table(
        name = "simple_chit_payout",
        uniqueConstraints = @UniqueConstraint(columnNames = {"chit_id", "month_index"})
)
public class SimpleChitPayout {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Setter(AccessLevel.NONE)
    private long id;

    @ManyToOne(optional = false, fetch = FetchType.LAZY)
    @JoinColumn(name = "chit_id", nullable = false)
    private SimpleChit chit;

    /** 1-based month number within the chit. */
    @Column(name = "month_index", nullable = false)
    private int monthIndex;

    @ManyToOne(optional = false, fetch = FetchType.LAZY)
    @JoinColumn(name = "member_id", nullable = false)
    private SimpleChitMember member;

    @Column(nullable = false)
    private double amount;

    @Column(name = "paid_on", nullable = false)
    private LocalDate paidOn;

    /** Amount added to the member's entries after monthIndex, for exact reversal on delete/replace. */
    @Column(name = "escalation_applied", nullable = false)
    @ColumnDefault("0")
    private double escalationApplied = 0;
}
