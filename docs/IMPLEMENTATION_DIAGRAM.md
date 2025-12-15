# Implementation Flow Diagrams

## 🔍 Detailed Component Flow

### 1. Main Processing Pipeline Flow

```mermaid
flowchart TD
    A[CLI Entry Point] --> B[ConfigManager]
    A --> C[AudioProcessingPipeline]

    B --> D[Load Profile]
    B --> E[Validate Configuration]
    E --> F[ProcessingConfig Object]

    C --> G[AudioLoader.load_audio]
    G --> H[Audio Data + Sample Rate]

    H --> I[DetectionEngine.detect_music]
    H --> J[DetectionEngine.detect_speech]
    H --> K[DetectionEngine.detect_silence]

    I --> L[Music Segments List]
    J --> M[Speech Segments List]
    K --> N[Silence Segments List]

    L --> O[SegmentationProcessor.process_segments]
    M --> O
    N --> O

    O --> P[Refined Segments]

    P --> Q{Transcription Enabled?}
    Q -->|Yes| R[STTModule.transcribe_segments]
    Q -->|No| S[Skip STT]

    R --> T[Enhanced Segments]
    S --> T

    T --> U[SemanticLabeler.label_segments]
    U --> V[Final Segments]

    V --> W[OutputGenerator.export]
    W --> X[JSON/CSV/TXT Files]
```

### 2. Detection Engine Internal Flow

```mermaid
flowchart TD
    A[DetectionEngine] --> B[Frame Processing]

    B --> C[Extract Features per Frame]
    C --> D[MFCC Coefficients]
    C --> E[Spectral Features]
    C --> F[Energy & ZCR]
    C --> G[Tempo Estimation]

    D --> H[MusicDetector]
    E --> H
    F --> H
    G --> H

    D --> I[SpeechDetector]
    E --> I
    F --> I

    F --> J[SilenceDetector]

    H --> K[Music Probability per Frame]
    I --> L[Speech Probability per Frame]
    J --> M[Silence Probability per Frame]

    K --> N[Threshold Analysis > 0.5]
    L --> N
    M --> N

    N --> O[Frame Classifications]
    O --> P[Temporal Smoothing]
    P --> Q[Segment Generation]
    Q --> R[Boundary Detection]
    R --> S[Initial Segments]
```

### 3. Classification Algorithm Flow

```mermaid
flowchart TD
    A[Audio Frame] --> B[Extract Features]

    B --> C{Music Detection}
    C -->|tempo > 60| D[+0.3 probability]
    C -->|zcr < 0.1| E[+0.2 probability]
    C -->|centroid > 2000| F[+0.15 probability]
    C -->|mfcc_stable| G[+0.2 probability]

    D --> H[Total Music Probability]
    E --> H
    F --> H
    G --> H

    H --> I{Music > 0.5?}
    I -->|Yes| J[Classify as Music]
    I -->|No| K[Check Speech]

    K --> L{Speech Detection}
    L -->|energy > 0.02| M[+0.3 probability]
    L -->|zcr > 0.1| N[+0.25 probability]
    L -->|centroid 500-2000| O[+0.15 probability]

    M --> P[Total Speech Probability]
    N --> P
    O --> P

    P --> Q{Speech > 0.5?}
    Q -->|Yes| R[Classify as Speech]
    Q -->|No| S[Classify as Silence]
```

### 4. Overlap Resolution Logic Flow

```mermaid
flowchart TD
    A[Segment Overlap Detected] --> B{Compare Confidences}

    B -->|Music > Speech| C[Keep Music Segment]
    B -->|Speech > Music| D[Keep Speech Segment]
    B -->|Similar Confidence| E[Duration-Based Decision]

    E --> F{Music Duration > Speech?}
    F -->|Yes| C
    F -->|No| D

    C --> G[Remove Overlapping Speech]
    D --> H[Remove Overlapping Music]

    G --> I[Resolved Segments]
    H --> I
```

### 5. STT Module Integration Flow

```mermaid
flowchart TD
    A[Speech Segments] --> B[Filter for Transcription]

    B --> C[Process Each Segment]
    C --> D[Resample to 16kHz]
    D --> E[Save to Temp File]
    E --> F[Whisper Model Load]

    F --> G{Whisper Model Loaded?}
    G -->|No| H[Load Model - takes ~4s]
    H --> I
    G -->|Yes| I

    I --> J[Transcribe with Whisper]
    J --> K[Extract Text & Confidence]
    K --> L[Update Segment Object]
    L --> M[Clean Up Temp File]

    M --> N{More Segments?}
    N -->|Yes| C
    N -->|No| O[Transcription Complete]
```

## 🔧 Configuration Flow

### Profile Loading and Validation

```mermaid
flowchart TD
    A[CLI --profile church_service] --> B[ConfigManager.load_profile]

    B --> C[Load Default Config]
    C --> D[Load Profile YAML]

    D --> E[Validate with JSON Schema]
    E --> F{Validation Pass?}

    F -->|Yes| G[Merge with CLI Overrides]
    F -->|No| H[Throw ValidationError]

    G --> I[Create ProcessingConfig Object]
    I --> J[Inject into Pipeline]
```

## 🚨 Problem Identification in Current Flow

### 1. Over-Categorization Points

```mermaid
flowchart TD
    A[Detection Phase] --> B[Independent Detection]
    B --> C[Music Detector - Aggressive]
    C --> D[174 Music Segments]

    B --> E[Speech Detector - Sensitive]
    E --> F[755 Speech Segments]

    B --> G[Silence Detector]
    G --> H[Silence Boundaries]

    D --> I[SegmentationProcessor]
    F --> I
    H --> I

    I --> J[Overlap Resolution - FLAWED]
    J --> K[Confidence-Based Only]
    K --> L[Boundary Optimization]

    L --> M[SemanticLabeler - AGGRESSIVE]
    M --> N[Genre Classification - NO CONFIDENCE]
    N --> O[Mood Detection - FORCED]
    O --> P[Profile Rules - CONFLICTING]

    P --> Q[Final Output: 1031 Music, 465 Speech, 459 Silence]
```

### 2. Current Overlap Resolution Issues

```mermaid
sequenceDiagram
    participant MD as MusicDetector
    participant SD as SpeechDetector
    participant SR as SegmentationProcessor
    participant SL as SemanticLabeler

    Note over MD,SD: Independent Detection
    MD->>SR: music_segments: 174 high-confidence
    SD->>SR: speech_segments: 755 moderate-confidence

    Note over SR: Flawed Conflict Resolution
    SR->>SR: _resolve_overlaps()
    Note right of SR: Keeps highest confidence only
    SR->>SR: Music wins many conflicts

    Note over SR: Semantic Enhancement Issues
    SR->>SL: segments with metadata
    SL->>SL: classify_genre() - always runs
    SL->>SL: apply_profile_rules() - conflicting rules

    SL->>SR: enhanced_segments: 1031 music!
    Note over SR,SL: 6x music increase!
```

## 🔍 Method-Level Implementation Details

### MusicDetector.detect_segments()

```python
def detect_segments(self, audio_data: np.ndarray, sr: int) -> list[AudioSegment]:
    # 1. Extract frame-level features
    features = self.extract_features(audio_data, sr)

    # 2. Calculate music probability per frame
    music_probs = []
    for frame in features:
        prob = 0.0
        if frame['tempo'] > 60: prob += 0.3
        if frame['zcr'] < 0.1: prob += 0.2
        if frame['spectral_centroid'] > 2000: prob += 0.15
        if frame['mfcc_stable']: prob += 0.2
        if frame['spectral_bandwidth'] > 1000: prob += 0.15
        music_probs.append(prob)

    # 3. Thresholding - PROBLEM HERE
    frames_above_threshold = [i for i, p in enumerate(music_probs) if p > 0.5]

    # 4. Segment generation - PROBLEM HERE
    segments = self._frames_to_segments(frames_above_threshold)

    # 5. Classification - PROBLEM HERE
    for segment in segments:
        segment.genre = self.classify_genre(segment.features)  # Always classifies!

    return segments
```

### SemanticLabeler.label_segments()

```mermaid
flowchart TD
    A[Input Segments] --> B[Process Each Segment]

    B --> C{Segment Duration > Min?}
    C -->|No| D[Skip Processing]
    C -->|Yes| E[Extract Features]

    E --> F[Classify Genre]
    F --> G[Classify Mood]
    G --> H[Apply Profile Rules]

    H --> I{Multiple Rules Match?}
    I -->|Yes| J[Priority Conflict - POOR]
    I -->|No| K[Apply Single Rule]

    J --> L[Keep Highest Priority]
    K --> M[Add Metadata]
    L --> M

    D --> N[Next Segment]
    M --> N
```

### Configuration Problem Points

```yaml
# church_service.yaml - CURRENT PROBLEMS
semantic_labeling:
  rules:
    # PROBLEM: No mutual exclusion between rules
    - label: "sermon"
      confidence_threshold: 0.7
      pattern:
        min_duration: 300  # 5 minutes
        silence_threshold: -35

    # PROBLEM: Conflicts with sermon rule
    - label: "worship_music"
      confidence_threshold: 0.6  # Lower threshold!
      pattern:
        min_duration: 60  # Can overlap with sermon
        has_tempo: true
```

## 📊 Performance Flow Analysis

### Current Processing Times

```mermaid
gantt
    title 48-Minute Audio Processing Timeline
    dateFormat X
    axisFormat %s

    section Loading
    Audio Load :0, 6

    section Detection
    Music Detection :6, 22
    Speech Detection :22, 38
    Silence Detection :38, 42

    section Segmentation
    Boundary Optimization :42, 54

    section Transcription
    STT Processing :54, 390  # ~6 minutes

    section Output
    JSON Export :390, 395
```

### Memory Usage Pattern

```mermaid
flowchart LR
    A[Audio File<br/>48MB] --> B[librosa.load<br/>129MB in memory]
    B --> C[Feature Extraction<br/>Additional 50MB]
    C --> D[Detection Results<br/>+5MB]
    D --> E[JSON Output<br/>1MB on disk]

    style B fill:#ffcccc
    style C fill:#ffcccc
    style D fill:#ccffcc
    style E fill:#ccffcc
```

This detailed implementation analysis reveals exactly where the over-categorization occurs and provides clear paths for fixing the issues in the detection and classification logic.