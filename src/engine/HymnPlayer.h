#ifndef HYMNPLAYER_H
#define HYMNPLAYER_H

#include <string>
#include <fluidsynth.h>

class HymnPlayer {
public:
    HymnPlayer(const std::string& soundfontPath = "/usr/share/sounds/sf2/FluidR3_GM.sf2");
    ~HymnPlayer();

    bool load(const std::string& filename);
    void play();
    void pause();
    void stop();

    bool isPlaying() const;
    void renderAudio(float* buffer, int numFrames);

private:
    bool playing;
    std::string currentFile;

    // FluidSynth components
    fluid_settings_t* settings;
    fluid_synth_t* synth;
    fluid_player_t* player;

    int soundfontId;
};

#endif // HYMNPLAYER_H
