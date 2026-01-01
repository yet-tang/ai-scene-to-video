package com.aiscene.dto;

import lombok.Data;

import java.util.Map;

@Data
public class CreateProjectRequest {
    private Long userId;
    private String title;
    private Map<String, Object> houseInfo; // room, hall, area, price
}
