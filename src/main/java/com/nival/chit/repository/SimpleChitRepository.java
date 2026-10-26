package com.nival.chit.repository;

import com.nival.chit.entity.SimpleChit;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * Repository for owner-scoped simple chits.
 */
@Repository
public interface SimpleChitRepository extends JpaRepository<SimpleChit, Long> {

    List<SimpleChit> findByOwnerIdOrderByCreatedAtDesc(Long ownerId);

    Optional<SimpleChit> findByIdAndOwnerId(Long id, Long ownerId);
}
