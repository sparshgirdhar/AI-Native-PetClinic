package org.example.mcpserver.dto;

import java.util.List;

public record VetListResponse(
	List<VetDto> vetList
) {}
