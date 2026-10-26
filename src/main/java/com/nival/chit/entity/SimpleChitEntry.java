package com.nival.chit.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.ColumnDefault;

import java.time.LocalDateTime;

/**
 * The amount recorded for one member in one month of a {@link SimpleChit}.
 */
@Entity
@Getter
@Setter
@Table(
        name = "simple_chit_entry",
        uniqueConstraints = @UniqueConstraint(columnNames = {"member_id", "month_index"})
)
public class SimpleChitEntry {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Setter(AccessLevel.NONE)
    private long id;

    @ManyToOne(optional = false, fetch = FetchType.LAZY)
    @JoinColumn(name = "member_id", nullable = false)
    private SimpleChitMember member;

    /** 1-based month number within the chit. */
    @Column(name = "month_index", nullable = false)
    private int monthIndex;

    @Column(nullable = false)
    private double amount;

    /** True once the member has actually paid this amount. New cells start pending. */
    @Column(nullable = false)
    @ColumnDefault("false")
    private boolean paid;

    /** When the cell was marked paid; null while pending. */
    @Column(name = "paid_at")
    private LocalDateTime paidAt;
}
