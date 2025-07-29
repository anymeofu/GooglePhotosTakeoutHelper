import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/gpth_core_api.dart';
import '../../domain/models/processing_config_model.dart';
import '../../domain/models/processing_result_model.dart';

/// Application state for the GPTH GUI
class AppState {
  const AppState({
    this.isInitialized = false,
    this.isProcessing = false,
    this.inputPath,
    this.outputPath,
    this.config,
    this.result,
    this.error,
    this.validationResult,
    this.spaceEstimate,
    this.exifToolInfo,
    this.processingProgress = 0.0,
    this.processingMessage,
  });

  final bool isInitialized;
  final bool isProcessing;
  final String? inputPath;
  final String? outputPath;
  final ProcessingConfig? config;
  final ProcessingResult? result;
  final String? error;
  final ValidationResult? validationResult;
  final SpaceEstimate? spaceEstimate;
  final ExifToolInfo? exifToolInfo;
  final double processingProgress;
  final String? processingMessage;

  AppState copyWith({
    bool? isInitialized,
    bool? isProcessing,
    String? inputPath,
    String? outputPath,
    ProcessingConfig? config,
    ProcessingResult? result,
    String? error,
    ValidationResult? validationResult,
    SpaceEstimate? spaceEstimate,
    ExifToolInfo? exifToolInfo,
    double? processingProgress,
    String? processingMessage,
  }) {
    return AppState(
      isInitialized: isInitialized ?? this.isInitialized,
      isProcessing: isProcessing ?? this.isProcessing,
      inputPath: inputPath ?? this.inputPath,
      outputPath: outputPath ?? this.outputPath,
      config: config ?? this.config,
      result: result ?? this.result,
      error: error ?? this.error,
      validationResult: validationResult ?? this.validationResult,
      spaceEstimate: spaceEstimate ?? this.spaceEstimate,
      exifToolInfo: exifToolInfo ?? this.exifToolInfo,
      processingProgress: processingProgress ?? this.processingProgress,
      processingMessage: processingMessage ?? this.processingMessage,
    );
  }
}

/// State notifier for managing the application state
class AppStateNotifier extends StateNotifier<AppState> {
  AppStateNotifier() : super(const AppState());

  /// Initialize the GPTH core API
  Future<void> initialize({bool verbose = false}) async {
    try {
      await GpthCoreApi.instance.initialize(verbose: verbose);
      
      // Check ExifTool status
      final exifInfo = await GpthCoreApi.instance.checkExifToolStatus();
      
      state = state.copyWith(
        isInitialized: true,
        exifToolInfo: exifInfo,
        error: null,
      );
    } catch (e) {
      state = state.copyWith(
        error: 'Failed to initialize: $e',
        isInitialized: false,
      );
    }
  }

  /// Set input directory path
  Future<void> setInputPath(String path) async {
    state = state.copyWith(inputPath: path);
    
    // Validate the directory structure
    try {
      final validation = await GpthCoreApi.instance.validateTakeoutStructure(path);
      state = state.copyWith(validationResult: validation);
      
      // If valid and we have an output path, calculate space estimate
      if (validation.isValid && state.outputPath != null) {
        await _updateSpaceEstimate();
      }
    } catch (e) {
      state = state.copyWith(
        error: 'Failed to validate input directory: $e',
      );
    }
  }

  /// Set output directory path
  void setOutputPath(String path) {
    state = state.copyWith(outputPath: path);
    
    // Update space estimate if we have input path
    if (state.inputPath != null && state.validationResult?.isValid == true) {
      _updateSpaceEstimate();
    }
  }

  /// Update space estimate based on current paths and album behavior
  Future<void> _updateSpaceEstimate([AlbumBehavior? albumBehavior]) async {
    if (state.inputPath == null) return;
    
    try {
      final behavior = albumBehavior ?? AlbumBehavior.shortcut;
      final estimate = await GpthCoreApi.instance.estimateSpaceRequirements(
        state.inputPath!,
        behavior,
      );
      
      state = state.copyWith(spaceEstimate: estimate);
    } catch (e) {
      // Space estimation failed, but don't show error to user
      // This is not critical for the app functionality
    }
  }

  /// Update space estimate with new album behavior
  Future<void> updateSpaceEstimate(AlbumBehavior albumBehavior) async {
    await _updateSpaceEstimate(albumBehavior);
  }

  /// Start processing with the given configuration
  Future<void> startProcessing(ProcessingConfig config) async {
    state = state.copyWith(
      isProcessing: true,
      config: config,
      result: null,
      error: null,
      processingProgress: 0.0,
      processingMessage: 'Starting processing...',
    );

    try {
      // Simulate progress updates (in real implementation, this would come from the pipeline)
      _simulateProgress();
      
      final result = await GpthCoreApi.instance.processGooglePhotos(config);
      
      state = state.copyWith(
        isProcessing: false,
        result: result,
        processingProgress: 1.0,
        processingMessage: result.isSuccess ? 'Processing completed successfully!' : 'Processing failed',
      );
    } catch (e) {
      state = state.copyWith(
        isProcessing: false,
        error: 'Processing failed: $e',
        processingMessage: 'Processing failed',
      );
    }
  }

  /// Simulate processing progress (replace with real progress reporting)
  void _simulateProgress() {
    // This is a placeholder - in a real implementation, you'd get progress
    // from the processing pipeline through callbacks or streams
    Future.delayed(const Duration(seconds: 1), () {
      if (state.isProcessing) {
        state = state.copyWith(
          processingProgress: 0.1,
          processingMessage: 'Fixing file extensions...',
        );
      }
    });
    
    Future.delayed(const Duration(seconds: 3), () {
      if (state.isProcessing) {
        state = state.copyWith(
          processingProgress: 0.2,
          processingMessage: 'Discovering media files...',
        );
      }
    });
    
    Future.delayed(const Duration(seconds: 5), () {
      if (state.isProcessing) {
        state = state.copyWith(
          processingProgress: 0.4,
          processingMessage: 'Removing duplicates...',
        );
      }
    });
    
    Future.delayed(const Duration(seconds: 8), () {
      if (state.isProcessing) {
        state = state.copyWith(
          processingProgress: 0.6,
          processingMessage: 'Extracting dates...',
        );
      }
    });
    
    Future.delayed(const Duration(seconds: 10), () {
      if (state.isProcessing) {
        state = state.copyWith(
          processingProgress: 0.8,
          processingMessage: 'Moving files...',
        );
      }
    });
  }

  /// Clear error state
  void clearError() {
    state = state.copyWith(error: null);
  }

  /// Reset the application state
  void reset() {
    state = const AppState();
  }

  /// Clean up resources
  Future<void> dispose() async {
    await GpthCoreApi.instance.dispose();
    state = const AppState();
  }
}

/// Provider for the application state
final appStateProvider = StateNotifierProvider<AppStateNotifier, AppState>((ref) {
  return AppStateNotifier();
});

/// Convenience providers for specific parts of the state
final isInitializedProvider = Provider<bool>((ref) {
  return ref.watch(appStateProvider.select((state) => state.isInitialized));
});

final isProcessingProvider = Provider<bool>((ref) {
  return ref.watch(appStateProvider.select((state) => state.isProcessing));
});

final inputPathProvider = Provider<String?>((ref) {
  return ref.watch(appStateProvider.select((state) => state.inputPath));
});

final outputPathProvider = Provider<String?>((ref) {
  return ref.watch(appStateProvider.select((state) => state.outputPath));
});

final validationResultProvider = Provider<ValidationResult?>((ref) {
  return ref.watch(appStateProvider.select((state) => state.validationResult));
});

final spaceEstimateProvider = Provider<SpaceEstimate?>((ref) {
  return ref.watch(appStateProvider.select((state) => state.spaceEstimate));
});

final exifToolInfoProvider = Provider<ExifToolInfo?>((ref) {
  return ref.watch(appStateProvider.select((state) => state.exifToolInfo));
});

final processingProgressProvider = Provider<double>((ref) {
  return ref.watch(appStateProvider.select((state) => state.processingProgress));
});

final processingMessageProvider = Provider<String?>((ref) {
  return ref.watch(appStateProvider.select((state) => state.processingMessage));
});

final errorProvider = Provider<String?>((ref) {
  return ref.watch(appStateProvider.select((state) => state.error));
});

final resultProvider = Provider<ProcessingResult?>((ref) {
  return ref.watch(appStateProvider.select((state) => state.result));
});