CXX = g++
CXXFLAGS = -std=c++11 -I.
LDFLAGS = -lfluidsynth

all: tests/run_tests

tests/run_tests: tests/HymnPlayerTests.cpp src/engine/HymnPlayer.cpp
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS)

clean:
	rm -f tests/run_tests
