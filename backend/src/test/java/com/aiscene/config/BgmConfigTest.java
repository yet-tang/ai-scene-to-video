package com.aiscene.config;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class BgmConfigTest {

    @Test
    void getRandomBgmUrl_returnsNullWhenListEmpty() {
        BgmConfig config = new BgmConfig();

        assertThat(config.getRandomBgmUrl()).isNull();
        assertThat(config.hasBuiltinBgm()).isFalse();
        assertThat(config.getBuiltinCount()).isEqualTo(0);
    }

    @Test
    void getRandomBgmUrl_returnsValueFromBuiltinList() {
        BgmConfig config = new BgmConfig();
        config.setBuiltinUrls(List.of("u1", "u2", "u3"));

        // Call multiple times to ensure it always returns one of the configured URLs
        for (int i = 0; i < 10; i++) {
            String url = config.getRandomBgmUrl();
            assertThat(url).isIn("u1", "u2", "u3");
        }

        assertThat(config.hasBuiltinBgm()).isTrue();
        assertThat(config.getBuiltinCount()).isEqualTo(3);
    }

    @Test
    void autoSelect_flagCanBeConfigured() {
        BgmConfig config = new BgmConfig();

        // Default is true
        assertThat(config.isAutoSelect()).isTrue();

        config.setAutoSelect(false);
        assertThat(config.isAutoSelect()).isFalse();
    }
}
