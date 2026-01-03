package com.aiscene.controller;

import org.junit.jupiter.api.Test;

import javax.sql.DataSource;
import java.sql.Connection;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class HealthControllerTest {

    @Test
    void health_returnsOk() {
        DataSource dataSource = mock(DataSource.class);
        HealthController controller = new HealthController(dataSource);
        assertThat(controller.health().getStatusCode().value()).isEqualTo(200);
        assertThat(controller.health().getBody()).isEqualTo("OK");
    }

    @Test
    void ready_returnsOkWhenDbValid() throws Exception {
        DataSource dataSource = mock(DataSource.class);
        Connection conn = mock(Connection.class);
        when(dataSource.getConnection()).thenReturn(conn);
        when(conn.isValid(1)).thenReturn(true);

        HealthController controller = new HealthController(dataSource);
        assertThat(controller.ready().getStatusCode().value()).isEqualTo(200);
        assertThat(controller.ready().getBody()).isEqualTo("OK");
    }

    @Test
    void ready_returns503WhenDbInvalid() throws Exception {
        DataSource dataSource = mock(DataSource.class);
        Connection conn = mock(Connection.class);
        when(dataSource.getConnection()).thenReturn(conn);
        when(conn.isValid(1)).thenReturn(false);

        HealthController controller = new HealthController(dataSource);
        assertThat(controller.ready().getStatusCode().value()).isEqualTo(503);
    }

    @Test
    void ready_returns503WhenDbThrows() throws Exception {
        DataSource dataSource = mock(DataSource.class);
        when(dataSource.getConnection()).thenThrow(new RuntimeException("x"));

        HealthController controller = new HealthController(dataSource);
        assertThat(controller.ready().getStatusCode().value()).isEqualTo(503);
    }
}

