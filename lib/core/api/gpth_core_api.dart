import 'dart:io';

import '../../domain/main_pipeline.dart';
import '../../domain/models/processing_config_model.dart';
import '../../domain/models/processing_result_model.dart';
import '../../domain/services/core/service_container.dart';
import '../../domain/services/user_interaction/user_interaction_service.dart';

/// Core API for Google Photos Takeout Helper
///
/// This class provides a clean interface to all GPTH functionality,
/// separating the business logic from the CLI interface to enable
/// integration with different user interfaces (CLI, GUI, etc.).
class GpthCoreApi {
  GpthCoreApi._();
  
  static GpthCoreApi? _instance;
  
  /// Get the singleton instance of the Core API
  static GpthCoreApi get instance {
    _instance ??= GpthCoreApi._();
    return _instance!;
  }
  
  bool _isInitialized = false;
  
  /// Initialize the core API and all required services
  Future<void> initialize({bool verbose = false}) async {
    if (_isInitialized) {
      return;
    }
    
    await ServiceContainer.instance.initialize();
    _isInitialized = true;
  }
  
  /// Dispose of all services and cleanup resources
  Future<void> dispose() async {
    await ServiceContainer.instance.dispose();
    _isInitialized = false;
  }
  
  /// Process Google Photos Takeout with the given configuration
  ///
  /// [config] - Processing configuration including input/output paths and options
  /// Returns comprehensive processing results including statistics and timing
  Future<ProcessingResult> processGooglePhotos(ProcessingConfig config) async {
    _ensureInitialized();
    
    // Validate configuration
    config.validate();
    
    // Ensure directories exist
    final inputDir = Directory(config.inputPath);
    final outputDir = Directory(config.outputPath);
    
    if (!await inputDir.exists()) {
      throw Exception('Input directory does not exist: ${config.inputPath}');
    }
    
    if (!await outputDir.exists()) {
      await outputDir.create(recursive: true);
    }
    
    // Create and execute the processing pipeline
    final pipeline = ProcessingPipeline();
    
    return await pipeline.execute(
      config: config,
      inputDirectory: inputDir,
      outputDirectory: outputDir,
    );
  }
  
  /// Validate a Google Photos Takeout directory structure
  ///
  /// [inputPath] - Path to the directory to validate
  /// Returns validation result with details about the structure
  Future<ValidationResult> validateTakeoutStructure(String inputPath) async {
    _ensureInitialized();
    
    final inputDir = Directory(inputPath);
    
    if (!await inputDir.exists()) {
      return ValidationResult(
        isValid: false,
        message: 'Directory does not exist',
        details: [],
      );
    }
    
    final details = <String>[];
    var isValid = true;
    
    // Check for basic Google Photos structure
    final entities = await inputDir.list().toList();
    final directories = entities.whereType<Directory>().toList();
    
    // Look for year folders (Photos from YYYY)
    final yearFolders = directories.where((dir) {
      final name = dir.path.split(Platform.pathSeparator).last.toLowerCase();
      return name.contains('photos from') && 
             RegExp(r'20\d{2}').hasMatch(name);
    }).toList();
    
    if (yearFolders.isNotEmpty) {
      details.add('Found ${yearFolders.length} year folder(s)');
    } else {
      details.add('No year folders found (Photos from YYYY)');
    }
    
    // Look for album folders
    final albumFolders = directories.where((dir) {
      final name = dir.path.split(Platform.pathSeparator).last.toLowerCase();
      return !name.contains('photos from') && 
             !name.startsWith('.') &&
             name != 'archive' &&
             name != 'trash';
    }).toList();
    
    if (albumFolders.isNotEmpty) {
      details.add('Found ${albumFolders.length} potential album folder(s)');
    }
    
    // Basic validation - need at least some folders
    if (yearFolders.isEmpty && albumFolders.isEmpty) {
      isValid = false;
      details.add('No recognizable Google Photos structure found');
    }
    
    return ValidationResult(
      isValid: isValid,
      message: isValid ? 'Valid Google Photos Takeout structure' : 'Invalid structure',
      details: details,
    );
  }
  
  /// Get estimated disk space requirements for processing
  ///
  /// [inputPath] - Path to the input directory
  /// [albumBehavior] - Album handling mode that affects space requirements
  /// Returns space estimation in bytes
  Future<SpaceEstimate> estimateSpaceRequirements(
    String inputPath, 
    AlbumBehavior albumBehavior,
  ) async {
    _ensureInitialized();
    
    final inputDir = Directory(inputPath);
    if (!await inputDir.exists()) {
      throw Exception('Input directory does not exist');
    }
    
    // Calculate current space usage
    int totalSize = 0;
    int fileCount = 0;
    
    await for (final entity in inputDir.list(recursive: true)) {
      if (entity is File) {
        try {
          totalSize += await entity.length();
          fileCount++;
        } catch (e) {
          // Skip inaccessible files
          continue;
        }
      }
    }
    
    // Estimate additional space needed based on album behavior
    double multiplier = 1.0; // Base space needed (moving files)
    
    switch (albumBehavior) {
      case AlbumBehavior.duplicateCopy:
        multiplier = 2.0; // Assumes average of 1 copy per album per file
        break;
      case AlbumBehavior.shortcut:
      case AlbumBehavior.reverseShortcut:
        multiplier = 1.1; // Small overhead for shortcuts
        break;
      case AlbumBehavior.json:
      case AlbumBehavior.nothing:
        multiplier = 1.0; // No additional space
        break;
    }
    
    final estimatedSpace = (totalSize * multiplier).round();
    
    return SpaceEstimate(
      currentSize: totalSize,
      estimatedRequiredSpace: estimatedSpace,
      fileCount: fileCount,
      albumBehavior: albumBehavior,
    );
  }
  
  /// Get available storage space for a given path
  ///
  /// [path] - Directory path to check available space
  /// Returns available space in bytes, or null if cannot be determined
  Future<int?> getAvailableSpace(String path) async {
    _ensureInitialized();
    
    return await ServiceContainer.instance.diskSpaceService.getAvailableSpace(path);
  }
  
  /// Check if ExifTool is available and properly configured
  ///
  /// Returns information about ExifTool availability and version
  Future<ExifToolInfo> checkExifToolStatus() async {
    _ensureInitialized();
    
    final exifTool = ServiceContainer.instance.exifTool;
    
    if (exifTool == null) {
      return ExifToolInfo(
        isAvailable: false,
        version: null,
        message: 'ExifTool not found. Some features may be limited.',
      );
    }
    
    try {
      final version = await exifTool.getVersion();
      return ExifToolInfo(
        isAvailable: true,
        version: version,
        message: 'ExifTool is available and ready',
      );
    } catch (e) {
      return ExifToolInfo(
        isAvailable: false,
        version: null,
        message: 'ExifTool found but not working properly: $e',
      );
    }
  }
  
  void _ensureInitialized() {
    if (!_isInitialized) {
      throw StateError('GpthCoreApi not initialized. Call initialize() first.');
    }
  }
}

/// Result of validating a Google Photos Takeout directory
class ValidationResult {
  const ValidationResult({
    required this.isValid,
    required this.message,
    required this.details,
  });
  
  final bool isValid;
  final String message;
  final List<String> details;
}

/// Estimated disk space requirements for processing
class SpaceEstimate {
  const SpaceEstimate({
    required this.currentSize,
    required this.estimatedRequiredSpace,
    required this.fileCount,
    required this.albumBehavior,
  });
  
  final int currentSize;
  final int estimatedRequiredSpace;
  final int fileCount;
  final AlbumBehavior albumBehavior;
  
  /// Additional space needed beyond current size
  int get additionalSpaceNeeded => estimatedRequiredSpace - currentSize;
  
  /// Space multiplier based on album behavior
  double get spaceMultiplier => estimatedRequiredSpace / currentSize;
}

/// Information about ExifTool availability and status
class ExifToolInfo {
  const ExifToolInfo({
    required this.isAvailable,
    required this.version,
    required this.message,
  });
  
  final bool isAvailable;
  final String? version;
  final String message;
}