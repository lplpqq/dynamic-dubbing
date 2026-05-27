def create_segments_from_peaks(word_timings, peaks, min_segment_duration=1.0):
    print("Creating segments aligned to peaks...")

    segments = []
    current_segment_words = []
    current_segment_start = word_timings[0]['start']
    peak_idx = 0

    for word in word_timings:
        current_segment_words.append(word)
        current_duration = word['end'] - current_segment_start

        should_close = False
        target_peak = None

        if peak_idx < len(peaks):
            if word['end'] >= peaks[peak_idx] and current_duration >= min_segment_duration:
                should_close = True
                target_peak = peaks[peak_idx]
                peak_idx += 1

        if should_close and len(current_segment_words) > 1:
            segment_text = ' '.join([w['word'] for w in current_segment_words])
            segment_end = current_segment_words[-1]['end']

            segments.append({
                'text_english': segment_text,
                'start': current_segment_start,
                'end': segment_end,
                'duration': segment_end - current_segment_start,
                'target_peak': target_peak,
                'segment_num': len(segments) + 1,
            })

            print(f"\nSegment {len(segments)}:")
            print(
                f"  Time: {current_segment_start:.2f}s -> {segment_end:.2f}s ({segment_end - current_segment_start:.2f}s)")
            print(f"  Peak at: {target_peak:.2f}s")
            print(f"  English: '{segment_text}'")

            current_segment_words = []
            current_segment_start = segment_end

    if current_segment_words:
        segment_text = ' '.join([w['word'] for w in current_segment_words])
        segment_end = current_segment_words[-1]['end']
        segments.append({
            'text_english': segment_text,
            'start': current_segment_start,
            'end': segment_end,
            'duration': segment_end - current_segment_start,
            'target_peak': None,
            'segment_num': len(segments) + 1,
        })

        print(f"\nSegment {len(segments)} (final):")
        print(f"  Time: {current_segment_start:.2f}s -> {segment_end:.2f}s ({segment_end - current_segment_start:.2f}s)")
        print(f"  English: '{segment_text}'")

    return segments


def mark_anchors_with_timing(text, segments, word_timings):
    print("\nMarking anchor points...")

    marked_text = text
    anchor_info = []

    for seg in segments:
        if seg['target_peak'] is None:
            continue

        peak_within_segment = seg['target_peak'] - seg['start']
        fraction_through = peak_within_segment / seg['duration']

        seg_words = [w for w in word_timings if seg['start'] <= (w['start'] + w['end']) / 2 < seg['end']]

        if seg_words:
            nearest_word = min(seg_words, key=lambda w: abs((w['start'] + w['end']) / 2 - seg['target_peak']))
            word_text = nearest_word['word']
            word_clean = word_text.rstrip('.,!?;:')

            if word_clean in marked_text:
                marked_text = marked_text.replace(word_clean, f"{word_clean} [PEAK at {fraction_through:.0%}]", 1)
                anchor_info.append({
                    'segment': seg['segment_num'],
                    'word': word_clean,
                    'peak_time': seg['target_peak'],
                    'fraction': fraction_through
                })

    print("Anchor points:")
    for info in anchor_info:
        print(
            f"  Segment {info['segment']}: '{info['word']}' at {info['fraction']:.0%} (time: {info['peak_time']:.2f}s)")

    return marked_text, anchor_info
