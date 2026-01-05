package com.aiscene.repository;

import com.aiscene.entity.Project;
import com.aiscene.entity.ProjectStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Collection;
import java.util.UUID;

@Repository
public interface ProjectRepository extends JpaRepository<Project, UUID> {
    Page<Project> findAllByUserId(Long userId, Pageable pageable);

    @Modifying
    @Query("update Project p set p.status = :nextStatus where p.id = :id and p.status in :allowed")
    int updateStatusIfIn(
            @Param("id") UUID id,
            @Param("allowed") Collection<ProjectStatus> allowed,
            @Param("nextStatus") ProjectStatus nextStatus);
}
