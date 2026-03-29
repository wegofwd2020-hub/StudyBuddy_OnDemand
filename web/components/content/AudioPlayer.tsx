"use client";

import { useEffect, useRef, useState } from "react";
import { Play, Pause, Volume2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useLessonAudioUrl } from "@/lib/hooks/useLesson";

interface AudioPlayerProps {
  unitId: string;
  onPlayed?: () => void;
}

export function AudioPlayer({ unitId, onPlayed }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [loadAudio, setLoadAudio] = useState(false);
  const playedRef = useRef(false);

  const { data: audioUrl, isLoading } = useLessonAudioUrl(unitId, loadAudio);

  // Set src once URL is available; update playing via the onPlay event instead
  useEffect(() => {
    if (audioUrl && audioRef.current) {
      audioRef.current.src = audioUrl;
      audioRef.current.play().catch(() => {});
    }
  }, [audioUrl]);

  function togglePlay() {
    if (!loadAudio) {
      setLoadAudio(true);
      return;
    }
    const el = audioRef.current;
    if (!el) return;
    if (playing) {
      el.pause();
      setPlaying(false);
    } else {
      el.play();
      setPlaying(true);
    }
  }

  function handleTimeUpdate() {
    const el = audioRef.current;
    if (!el || !el.duration) return;
    setProgress((el.currentTime / el.duration) * 100);
    if (!playedRef.current && el.currentTime > 5) {
      playedRef.current = true;
      onPlayed?.();
    }
  }

  function handleEnded() {
    setPlaying(false);
    setProgress(100);
  }

  function handleSeek(e: React.ChangeEvent<HTMLInputElement>) {
    const el = audioRef.current;
    if (!el || !el.duration) return;
    el.currentTime = (Number(e.target.value) / 100) * el.duration;
  }

  return (
    <div className="flex items-center gap-3 rounded-lg border bg-white p-3 shadow-sm">
      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-50">
        <Volume2 className="h-4 w-4 text-blue-600" />
      </div>

      <Button
        size="sm"
        variant="ghost"
        onClick={togglePlay}
        disabled={isLoading}
        aria-label={playing ? "Pause audio" : "Play audio"}
      >
        {isLoading ? (
          <span className="text-xs text-gray-400">Loading…</span>
        ) : playing ? (
          <Pause className="h-4 w-4" />
        ) : (
          <Play className="h-4 w-4" />
        )}
      </Button>

      <input
        type="range"
        min={0}
        max={100}
        value={progress}
        onChange={handleSeek}
        className="h-1 flex-1 accent-blue-600"
        aria-label="Audio progress"
      />

      <audio
        ref={audioRef}
        onPlay={() => setPlaying(true)}
        onTimeUpdate={handleTimeUpdate}
        onEnded={handleEnded}
        onError={() => setPlaying(false)}
      />
    </div>
  );
}
