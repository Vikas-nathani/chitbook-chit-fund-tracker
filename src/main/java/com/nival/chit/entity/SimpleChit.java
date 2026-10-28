package com.nival.chit.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.ColumnDefault;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * A lightweight chit tracked by a single owner: a total amount, a fixed list of
 * member names, and a fixed number of months. Independent of {@link ChitGroup}
 * (no auctions, loans, or memberships).
 *
 * <p>Uses {@code @Getter/@Setter} rather than {@code @Data} to avoid recursive
 * equals/hashCode/toString across the bidirectional member relations.</p>
 */
@Entity
@Getter
@Setter
@Table(name = "simple_chit")
@EntityListeners(AuditingEntityListener.class)
public class SimpleChit {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Setter(AccessLevel.NONE)
    private long id;

    @Column(nullable = false, length = 100)
    private String name;

    @Column(name = "total_amount", nullable = false)
    private double totalAmount;

    @Column(nullable = false)
    private int months;

    /** Owner's commission as a percent of the chit amount per month (target earning). */
    @Column(name = "commission_percent", nullable = false)
    @ColumnDefault("5")
    private double commissionPercent = 5;

    /** First month of the chit in {@code yyyy-MM} format, used for column labels. */
    @Column(name = "start_month", nullable = false, length = 7)
    private String startMonth;

    /** The one common monthly slot amount for this chit; a member's entry = this times their shares. */
    @Column(name = "per_share_amount", nullable = false)
    private double perShareAmount;

    /** Whether a member's remaining months go up after they take a payout. */
    @Column(name = "escalation_enabled", nullable = false)
    @ColumnDefault("false")
    private boolean escalationEnabled = false;

    /** Percent of totalAmount added to the taking member's remaining months, when escalation is enabled. */
    @Column(name = "escalation_percent", nullable = false)
    @ColumnDefault("1")
    private double escalationPercent = 1;

    @ManyToOne(optional = false, fetch = FetchType.LAZY)
    @JoinColumn(name = "owner_id", nullable = false)
    private User owner;

    @OneToMany(mappedBy = "chit", cascade = CascadeType.ALL, orphanRemoval = true)
    @OrderBy("position ASC")
    private List<SimpleChitMember> members = new ArrayList<>();

    /** At most one payout per month: the member who took that month's pot. */
    @OneToMany(mappedBy = "chit", cascade = CascadeType.ALL, orphanRemoval = true)
    @OrderBy("monthIndex ASC")
    private List<SimpleChitPayout> payouts = new ArrayList<>();

    @Column(name = "created_at", updatable = false)
    @CreatedDate
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    @LastModifiedDate
    private LocalDateTime updatedAt;
}
