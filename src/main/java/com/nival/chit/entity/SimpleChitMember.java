package com.nival.chit.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.Setter;

import java.util.ArrayList;
import java.util.List;

/**
 * A named participant in a {@link SimpleChit}. Not a login user.
 */
@Entity
@Getter
@Setter
@Table(name = "simple_chit_member")
public class SimpleChitMember {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Setter(AccessLevel.NONE)
    private long id;

    @ManyToOne(optional = false, fetch = FetchType.LAZY)
    @JoinColumn(name = "chit_id", nullable = false)
    private SimpleChit chit;

    @Column(nullable = false, length = 100)
    private String name;

    /** Display order within the chit, starting at 0. */
    @Column(nullable = false)
    private int position;

    @OneToMany(mappedBy = "member", cascade = CascadeType.ALL, orphanRemoval = true)
    @OrderBy("monthIndex ASC")
    private List<SimpleChitEntry> entries = new ArrayList<>();
}
