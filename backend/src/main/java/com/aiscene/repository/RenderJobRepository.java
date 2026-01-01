package com.aiscene.repository;

import com.aiscene.entity.RenderJob;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.UUID;

@Repository
public interface RenderJobRepository extends JpaRepository<RenderJob, UUID> {
}
