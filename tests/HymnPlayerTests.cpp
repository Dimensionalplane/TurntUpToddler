#include <iostream>
#include "src/engine/HymnPlayer.h"

// Simple test framework
#define ASSERT_TRUE(condition) \
    if (!(condition)) { \
        std::cerr << "Assertion failed: " << #condition << " at " << __FILE__ << ":" << __LINE__ << std::endl; \
        return 1; \
    }

#define ASSERT_FALSE(condition) \
    if (condition) { \
        std::cerr << "Assertion failed: " << #condition << " at " << __FILE__ << ":" << __LINE__ << std::endl; \
        return 1; \
    }

int main() {
    HymnPlayer player;

    // Initial state
    ASSERT_FALSE(player.isPlaying());

    // Load file
    ASSERT_TRUE(player.load("dummy.mid"));

    // Play
    player.play();
    ASSERT_TRUE(player.isPlaying());

    // Pause
    player.pause();
    ASSERT_FALSE(player.isPlaying());

    // Stop
    player.stop();
    ASSERT_FALSE(player.isPlaying());

    std::cout << "All HymnPlayer tests passed successfully." << std::endl;
    return 0;
}
