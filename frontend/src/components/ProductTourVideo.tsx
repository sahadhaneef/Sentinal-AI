import { useCallback, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';
import { tourChapters, tourDuration } from '../content/videoTour';

const timestamp = (seconds: number) =>
  `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;

export function ProductTourVideo() {
  const video = useRef<HTMLVideoElement>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [chapter, setChapter] = useState(0);
  const syncReady = useCallback(() => {
    const loaded = Boolean(
      video.current && video.current.readyState >= 1 && Number.isFinite(video.current.duration),
    );
    setReady(loaded);
    if (loaded) setFailed(false);
  }, []);
  const attachVideo = useCallback(
    (element: HTMLVideoElement | null) => {
      video.current = element;
      syncReady();
    },
    [syncReady],
  );
  return (
    <article className="product-tour-video" aria-labelledby="product-tour-title">
      <div className="tour-video-frame">
        <video
          ref={attachVideo}
          controls
          playsInline
          preload="metadata"
          poster="/media/sentinel-tour-poster.jpg"
          aria-label="SENTINEL AI: six agents and guided workspace tour"
          aria-describedby="product-tour-description"
          onLoadedMetadata={syncReady}
          onLoadedData={syncReady}
          onCanPlay={syncReady}
          onDurationChange={syncReady}
          onError={(event) => {
            // A failed caption/source request does not necessarily make the video unplayable.
            if (event.currentTarget.error) {
              setFailed(true);
              setReady(false);
            }
          }}
          onTimeUpdate={() => {
            const time = video.current?.currentTime ?? 0;
            setChapter(
              tourChapters.reduce<number>(
                (last, item, index) => (item.start <= time ? index : last),
                0,
              ),
            );
          }}
        >
          <source src="/media/sentinel-tour.mp4" type="video/mp4" />
          <track
            kind="captions"
            src="/media/sentinel-tour.vtt"
            srcLang="en"
            label="English"
            default
          />
          Your browser cannot play this video. Use the transcript below.
        </video>
      </div>
      <div className="tour-video-body">
        <div className="tour-video-heading">
          <h3 id="product-tour-title">Six agents. A guided tour.</h3>
          <span>{timestamp(tourDuration)}</span>
        </div>
        <p id="product-tour-description">
          Meet each agent, follow the human review checkpoint, and find your way around the
          workspace. Narrated with English captions. All activity shown is simulated.
        </p>
        {failed && (
          <p role="status">
            The video could not load. You can read the transcript or open the interactive
            walkthrough below.
          </p>
        )}
        <label className="tour-chapter-select">
          Jump to a chapter
          <select
            aria-label="Video chapter"
            disabled={!ready}
            value={chapter}
            onChange={(event) => {
              const next = Number(event.target.value);
              if (video.current && ready) {
                video.current.currentTime = tourChapters[next].start;
                setChapter(next);
              }
            }}
          >
            {tourChapters.map((item, index) => (
              <option key={item.id} value={index}>
                {timestamp(item.start)} · {item.title}
              </option>
            ))}
          </select>
        </label>
        <Link className="text-link" to="/demo">
          Open the interactive walkthrough <ArrowUpRight size={15} />
        </Link>
        <details className="tour-video-transcript">
          <summary>Read the video transcript</summary>
          <ol>
            {tourChapters.map((item) => (
              <li key={item.id}>
                <strong>
                  {timestamp(item.start)} · {item.title}
                </strong>
                <p>{item.narration}</p>
              </li>
            ))}
          </ol>
        </details>
      </div>
    </article>
  );
}
