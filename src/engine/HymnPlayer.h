#ifndef HYMNPLAYER_H
#define HYMNPLAYER_H

#include <string>
#include <vector>

class HymnPlayer {
public:
    HymnPlayer();
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
    // Add internal state for fluid synth or other rendering engine here
};

#endif // HYMNPLAYER_H
