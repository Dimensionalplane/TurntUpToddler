#include "HymnPlayer.h"
#include <iostream>
#include <stdexcept>

HymnPlayer::HymnPlayer(const std::string& soundfontPath) : playing(false), soundfontId(-1) {
    // Initialize FluidSynth settings
    settings = new_fluid_settings();
    if (!settings) {
        throw std::runtime_error("Failed to create FluidSynth settings");
    }

    // Initialize synthesizer
    synth = new_fluid_synth(settings);
    if (!synth) {
        delete_fluid_settings(settings);
        throw std::runtime_error("Failed to create FluidSynth synthesizer");
    }

    // Initialize player
    player = new_fluid_player(synth);
    if (!player) {
        delete_fluid_synth(synth);
        delete_fluid_settings(settings);
        throw std::runtime_error("Failed to create FluidSynth player");
    }

    // Load soundfont
    soundfontId = fluid_synth_sfload(synth, soundfontPath.c_str(), 1);
    if (soundfontId == -1) {
        std::cerr << "Warning: Failed to load soundfont: " << soundfontPath << std::endl;
        std::cerr << "Audio rendering may be silent." << std::endl;
    }
}

HymnPlayer::~HymnPlayer() {
    if (player) {
        fluid_player_stop(player);
        delete_fluid_player(player);
    }
    if (synth) {
        if (soundfontId != -1) {
            fluid_synth_sfunload(synth, soundfontId, 1);
        }
        delete_fluid_synth(synth);
    }
    if (settings) {
        delete_fluid_settings(settings);
    }
}

bool HymnPlayer::load(const std::string& filename) {
    if (player) {
        // Stop current playback
        stop();

        // Add MIDI file to player
        if (fluid_player_add(player, filename.c_str()) == FLUID_OK) {
            currentFile = filename;
            std::cout << "Loading hymn file: " << filename << std::endl;
            return true;
        } else {
            std::cerr << "Error: Failed to load MIDI file: " << filename << std::endl;
            return false;
        }
    }
    return false;
}

void HymnPlayer::play() {
    if (player && !currentFile.empty()) {
        if (fluid_player_play(player) == FLUID_OK) {
            playing = true;
            std::cout << "Playing hymn." << std::endl;
        } else {
            std::cerr << "Error: Failed to start playback." << std::endl;
        }
    }
}

void HymnPlayer::pause() {
    if (playing && player) {
        // FluidSynth doesn't have a direct pause for the synth rendering,
        // but we can stop the player and manage state
        fluid_player_stop(player);
        playing = false;
        std::cout << "Pausing hymn." << std::endl;
    }
}

void HymnPlayer::stop() {
    if (player) {
        fluid_player_stop(player);
        // Note: Resetting player might require re-adding the file or seeking
        playing = false;
        std::cout << "Stopping hymn." << std::endl;
    }
}

bool HymnPlayer::isPlaying() const {
    return playing && fluid_player_get_status(player) == FLUID_PLAYER_PLAYING;
}

void HymnPlayer::renderAudio(float* buffer, int numFrames) {
    if (isPlaying() && synth) {
        // Ensure buffer is cleared before writing
        for (int i = 0; i < numFrames * 2; ++i) {
            buffer[i] = 0.0f;
        }

        // Render audio - interleaved stereo
        // fluid_synth_write_float parameters: synth, len, lout, loff, rout, roff
        // For interleaved stereo: lout = buffer, rout = buffer + 1, stride = 2
        fluid_synth_write_float(synth, numFrames, buffer, 0, 2, buffer + 1, 0, 2);
    } else {
        // Output silence
        for (int i = 0; i < numFrames * 2; ++i) {
            buffer[i] = 0.0f;
        }
    }
}
