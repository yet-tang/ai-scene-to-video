package com.aiscene.config;

import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.UUID;

@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
@Slf4j
public class RequestLoggingFilter implements Filter {

    private static final String REQUEST_ID_HEADER = "X-Request-Id";
    private static final String MDC_KEY_REQ = "request_id";
    private static final String USER_ID_HEADER = "X-User-Id";
    private static final String MDC_KEY_USER = "user_id";

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        
        if (!(request instanceof HttpServletRequest httpRequest) || !(response instanceof HttpServletResponse httpResponse)) {
            chain.doFilter(request, response);
            return;
        }

        // 1. Get or Generate Request ID
        String requestId = httpRequest.getHeader(REQUEST_ID_HEADER);
        if (requestId == null || requestId.isEmpty()) {
            requestId = UUID.randomUUID().toString();
        }

        // 2. Put into MDC for logging
        MDC.put(MDC_KEY_REQ, requestId);
        
        // 2.1. Put User ID into MDC if present
        String userId = httpRequest.getHeader(USER_ID_HEADER);
        if (userId != null && !userId.isEmpty()) {
            MDC.put(MDC_KEY_USER, userId);
        }

        // 3. Add to Response Header
        httpResponse.setHeader(REQUEST_ID_HEADER, requestId);

        long startTime = System.currentTimeMillis();
        try {
            chain.doFilter(request, response);
        } finally {
            long duration = System.currentTimeMillis() - startTime;
            
            // 4. Log the request summary (Ops Rule: method, path, status, duration)
            log.info("Request: method={} path={} status={} duration_ms={}",
                    httpRequest.getMethod(),
                    httpRequest.getRequestURI(),
                    httpResponse.getStatus(),
                    duration);
            
            MDC.remove(MDC_KEY_REQ);
            MDC.remove(MDC_KEY_USER);
        }
    }
}
