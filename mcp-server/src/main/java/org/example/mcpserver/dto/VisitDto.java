package org.example.mcpserver.dto;

import java.time.LocalDate;

public record VisitDto(
	Integer id,
	LocalDate date,
	String description
) {}
