"use client";

import React, { createContext, useContext, useState } from 'react';

interface SettingsContextType {
  generateVocals: boolean;
  setGenerateVocals: (val: boolean) => void;
  normalizeAudio: boolean;
  setNormalizeAudio: (val: boolean) => void;
  kidsMode: boolean;
  setKidsMode: (val: boolean) => void;
  useAdvancedVideo: boolean;
  setUseAdvancedVideo: (val: boolean) => void;
  stylePrompt: string;
  setStylePrompt: (val: string) => void;
  interactiveMode: boolean;
  setInteractiveMode: (val: boolean) => void;
  remakePriority: "suno" | "replicate";
  setRemakePriority: (val: "suno" | "replicate") => void;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [generateVocals, setGenerateVocals] = useState(false);
  const [normalizeAudio, setNormalizeAudio] = useState(true);
  const [kidsMode, setKidsMode] = useState(false);
  const [useAdvancedVideo, setUseAdvancedVideo] = useState(false);
  const [stylePrompt, setStylePrompt] = useState("Deep House, high quality, electronic");
  const [interactiveMode, setInteractiveMode] = useState(false);
  const [remakePriority, setRemakePriority] = useState<"suno" | "replicate">("suno");

  return (
    <SettingsContext.Provider value={{
      generateVocals, setGenerateVocals,
      normalizeAudio, setNormalizeAudio,
      kidsMode, setKidsMode,
      useAdvancedVideo, setUseAdvancedVideo,
      stylePrompt, setStylePrompt,
      interactiveMode, setInteractiveMode,
      remakePriority, setRemakePriority
    }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const context = useContext(SettingsContext);
  if (context === undefined) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
}
