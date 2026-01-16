package com.aiscene.admin.controller;

import com.aiscene.admin.dto.ModelStatusResponse;
import com.aiscene.admin.service.ModelMonitorService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

/**
 * 模型监控控制器
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Slf4j
@RestController
@RequestMapping("/admin/models")
@RequiredArgsConstructor
public class ModelMonitorController {

    private final ModelMonitorService modelMonitorService;

    /**
     * 获取所有模型状态
     *
     * @return 模型状态列表
     */
    @GetMapping
    public ResponseEntity<List<ModelStatusResponse>> listModels() {
        List<ModelStatusResponse> models = modelMonitorService.listModels();
        return ResponseEntity.ok(models);
    }

    /**
     * 获取单个模型状态
     *
     * @param id 模型ID
     * @return 模型状态
     */
    @GetMapping("/{id}")
    public ResponseEntity<ModelStatusResponse> getModel(@PathVariable UUID id) {
        ModelStatusResponse model = modelMonitorService.getModel(id);
        return ResponseEntity.ok(model);
    }

    /**
     * 测试模型连通性
     *
     * @param id 模型ID
     * @return 测试结果
     */
    @PostMapping("/{id}/test")
    public ResponseEntity<ModelStatusResponse> testModel(@PathVariable UUID id) {
        log.info("Testing model connectivity: {}", id);
        ModelStatusResponse result = modelMonitorService.testModel(id);
        return ResponseEntity.ok(result);
    }
}
