package org.example.mcpserver.config;

import org.example.mcpserver.tools.PetClinicTools;
import org.springframework.ai.tool.ToolCallbackProvider;
import org.springframework.ai.tool.method.MethodToolCallbackProvider;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class McpToolConfig {

	@Bean
	public ToolCallbackProvider petClinicToolProvider(
		PetClinicTools petClinicTools) {

		return MethodToolCallbackProvider.builder()
			.toolObjects(petClinicTools)
			.build();
	}
}
