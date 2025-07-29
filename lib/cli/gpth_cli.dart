import 'dart:io';

import 'package:args/args.dart';

import '../core/api/gpth_core_api.dart';
import '../domain/models/processing_config_model.dart';
import '../domain/services/core/logging_service.dart';
import '../domain/services/core/service_container.dart';
import '../domain/services/user_interaction/path_resolver_service.dart';
import '../presentation/interactive_presenter.dart';
import '../shared/constants.dart';
import 'package:path/path.dart' as p;

/// Command Line Interface for Google Photos Takeout Helper
///
/// This class handles all CLI-specific functionality while delegating
/// the actual processing to the core API. This separation allows for
/// easy integration of different user interfaces.
class GpthCli {
  GpthCli({
    this.enableInteractive = true,
    this.enableProgressReporting = true,
  });
  
  final bool enableInteractive;
  final bool enableProgressReporting;
  
  late LoggingService _logger;
  
  /// Main entry point for CLI application
  Future<void> run(List<String> arguments) async {
    // Initialize logger early with default settings
    _logger = LoggingService();
    
    try {
      // Parse command line arguments
      final config = await _parseArguments(arguments);
      if (config == null) {
        return; // Help was shown or other early exit
      }
      
      // Update logger with correct verbosity
      _logger = LoggingService(isVerbose: config.verbose);
      
      // Initialize the core API
      await GpthCoreApi.instance.initialize(verbose: config.verbose);
      
      // Execute the processing
      final result = await _executeProcessing(config);
      
      // Show final results
      _showResults(config, result);
      
      // Cleanup
      await GpthCoreApi.instance.dispose();
    } catch (e) {
      _logger.error('Fatal error: $e');
      exit(1);
    }
  }
  
  /// Parse command line arguments and build configuration
  Future<ProcessingConfig?> _parseArguments(List<String> arguments) async {
    final parser = _createArgumentParser();
    
    try {
      final res = parser.parse(arguments);
      
      if (res['help']) {
        _showHelp(parser);
        return null;
      }
      
      // Convert ArgResults to configuration
      return await _buildConfigFromArgs(res);
    } on FormatException catch (e) {
      _logger.error('$e');
      exit(2);
    }
  }
  
  /// Create the command line argument parser
  ArgParser _createArgumentParser() => ArgParser()
    ..addFlag('help', abbr: 'h', negatable: false)
    ..addOption('fix', help: 'Folder with any photos to fix dates (special mode)')
    ..addFlag('interactive', help: 'Use interactive mode')
    ..addFlag('verbose', abbr: 'v', help: 'Shows extensive output')
    ..addOption('input', abbr: 'i', help: 'Input folder with extracted takeouts')
    ..addOption('output', abbr: 'o', help: 'Output folder for organized photos')
    ..addOption(
      'albums',
      help: 'What to do about albums?',
      allowed: InteractivePresenter.albumOptions.keys,
      allowedHelp: InteractivePresenter.albumOptions,
      defaultsTo: 'shortcut',
    )
    ..addOption(
      'divide-to-dates',
      help: 'Divide output to folders by nothing/year/month/day',
      allowed: ['0', '1', '2', '3'],
      defaultsTo: '0',
    )
    ..addFlag('skip-extras', help: 'Skip extra images (like -edited etc)')
    ..addFlag(
      'guess-from-name',
      help: 'Try to guess file dates from their names',
      defaultsTo: true,
    )
    ..addOption(
      'fix-extensions',
      help: 'Fix incorrect file extensions',
      allowed: ['none', 'standard', 'conservative', 'solo'],
      allowedHelp: {
        'none': 'No extension fixing',
        'standard': 'Fix extensions (skip TIFF-based files) - Default',
        'conservative': 'Fix extensions (skip TIFF and JPEG files)',
        'solo': 'Fix extensions then exit immediately',
      },
      defaultsTo: 'standard',
    )
    ..addFlag('transform-pixel-mp', help: 'Transform Pixel .MP/.MV to .mp4')
    ..addFlag(
      'update-creation-time',
      help: 'Set creation time equal to modification date (Windows only)',
    )
    ..addFlag(
      'write-exif',
      help: 'Write geodata and DateTime to EXIF (requires ExifTool for non-JPEG)',
      defaultsTo: true,
    )
    ..addFlag(
      'limit-filesize',
      help: 'Enforces 64MB file size limit for low RAM systems',
    )
    ..addFlag(
      'divide-partner-shared',
      help: 'Move partner shared media to separate folder (PARTNER_SHARED)',
    );
  
  /// Show help information
  void _showHelp(ArgParser parser) {
    print('''GooglePhotosTakeoutHelper v$version - The Dart successor

gpth is meant to help you with exporting your photos from Google Photos.

First, go to https://takeout.google.com/ , deselect all and select only Photos.
When ready, download all .zips, and extract them into *one* folder.
To read and write exif data, you have to install exiftool (e.g. from here https://exiftool.org)
for your OS and make sure the executable is in a folder in the \$PATH.

Then, run: gpth --input "folder/with/all/takeouts" --output "your/output/folder"
...and gpth will parse and organize all photos into one big chronological folder

${parser.usage}''');
  }
  
  /// Build configuration from parsed arguments
  Future<ProcessingConfig> _buildConfigFromArgs(ArgResults res) async {
    // Handle special fix mode
    if (res['fix'] != null) {
      return _handleFixMode(res);
    }
    
    // Set up interactive mode if needed
    final isInteractiveMode = enableInteractive && 
        (res['interactive'] || (res.arguments.isEmpty && stdin.hasTerminal));
    
    // Get input/output paths (interactive or from args)
    final paths = await _getInputOutputPaths(res, isInteractiveMode);
    
    // Build configuration using the builder pattern
    final configBuilder = ProcessingConfig.builder(
      inputPath: paths.inputPath,
      outputPath: paths.outputPath,
    );
    
    // Apply all configuration options
    if (res['verbose']) configBuilder.verboseOutput = true;
    if (res['skip-extras']) configBuilder.skipExtras = true;
    if (!res['guess-from-name']) configBuilder.guessFromName = false;
    
    // Set album behavior
    final albumBehavior = AlbumBehavior.fromString(res['albums']);
    configBuilder.albumBehavior = albumBehavior;
    
    // Set extension fixing mode
    ExtensionFixingMode extensionFixingMode;
    if (isInteractiveMode) {
      // Interactive mode for various options
      await _configureInteractiveOptions(configBuilder);
      extensionFixingMode = await _askExtensionFixing();
    } else {
      // Use command line arguments or defaults
      final divisionLevel = DateDivisionLevel.fromInt(
        int.parse(res['divide-to-dates']),
      );
      configBuilder.dateDivision = divisionLevel;
      
      final fixExtensionsArg = res['fix-extensions'] ?? 'standard';
      extensionFixingMode = ExtensionFixingMode.fromString(fixExtensionsArg);
      
      // Apply remaining configuration options from command line
      if (!res['write-exif']) configBuilder.exifWriting = false;
      if (res['transform-pixel-mp']) configBuilder.pixelTransformation = true;
      if (res['update-creation-time']) configBuilder.creationTimeUpdate = true;
      if (res['limit-filesize']) configBuilder.fileSizeLimit = true;
      if (res['divide-partner-shared']) configBuilder.dividePartnerShared = true;
    }
    
    configBuilder.extensionFixing = extensionFixingMode;
    
    return configBuilder.build();
  }
  
  /// Handle fix mode configuration
  Future<ProcessingConfig> _handleFixMode(ArgResults res) async {
    final fixPath = res['fix'] as String;
    
    final builder = ProcessingConfig.builder(
      inputPath: fixPath,
      outputPath: fixPath,
    );
    
    builder.verboseOutput = res['verbose'];
    builder.guessFromName = res['guess-from-name'];
    return builder.build();
  }
  
  /// Configure interactive options
  Future<void> _configureInteractiveOptions(ProcessingConfigBuilder configBuilder) async {
    if (!enableInteractive) return;
    
    // Ask user for date division preference
    print('');
    final dateDivision = await ServiceContainer.instance.interactiveService.askDivideDates();
    final divisionLevel = DateDivisionLevel.fromInt(dateDivision);
    configBuilder.dateDivision = divisionLevel;
    
    // Ask user for EXIF writing preference
    print('');
    final writeExif = await ServiceContainer.instance.interactiveService.askIfWriteExif();
    configBuilder.exifWriting = writeExif;
    
    // Ask user for Pixel/MP file transformation
    print('');
    final transformPixelMP = await ServiceContainer.instance.interactiveService.askTransformPixelMP();
    configBuilder.pixelTransformation = transformPixelMP;
    
    // Ask user for file size limiting
    print('');
    final limitFileSize = await ServiceContainer.instance.interactiveService.askIfLimitFileSize();
    configBuilder.fileSizeLimit = limitFileSize;
    
    // Ask user for creation time update (Windows only)
    if (Platform.isWindows) {
      print('');
      final updateCreationTime = await ServiceContainer.instance.interactiveService.askChangeCreationTime();
      configBuilder.creationTimeUpdate = updateCreationTime;
    }
    
    configBuilder.interactiveMode = true;
  }
  
  /// Ask for extension fixing mode in interactive mode
  Future<ExtensionFixingMode> _askExtensionFixing() async {
    if (!enableInteractive) return ExtensionFixingMode.standard;
    
    print('');
    final extensionFixingChoice = await ServiceContainer.instance.interactiveService.askFixExtensions();
    return ExtensionFixingMode.fromString(extensionFixingChoice);
  }
  
  /// Get input and output paths from arguments or interactive mode
  Future<InputOutputPaths> _getInputOutputPaths(
    ArgResults res,
    bool isInteractiveMode,
  ) async {
    String? inputPath = res['input'];
    String? outputPath = res['output'];
    
    if (isInteractiveMode && enableInteractive) {
      // Interactive mode handles path collection
      await ServiceContainer.instance.interactiveService.showGreeting();
      print('');
      
      final bool shouldUnzip = await ServiceContainer.instance.interactiveService.askIfUnzip();
      print('');
      
      late Directory inDir;
      if (shouldUnzip) {
        final zips = await ServiceContainer.instance.interactiveService.selectZipFiles();
        print('');
        
        final extractDir = await ServiceContainer.instance.interactiveService.selectExtractionDirectory();
        print('');
        
        final out = await ServiceContainer.instance.interactiveService.selectOutputDirectory();
        print('');
        
        // Calculate space requirements
        final cumZipsSize = zips
            .map((e) => e.lengthSync())
            .reduce((a, b) => a + b);
        final requiredSpace = (cumZipsSize * 2) + 256 * 1024 * 1024;
        
        await ServiceContainer.instance.interactiveService.freeSpaceNotice(
          requiredSpace,
          extractDir,
        );
        print('');
        
        inDir = extractDir;
        outputPath = out.path;
        
        await ServiceContainer.instance.interactiveService.extractAll(zips, extractDir);
        print('');
      } else {
        try {
          inDir = await ServiceContainer.instance.interactiveService.selectInputDirectory();
        } catch (e) {
          _logger.warning('⚠️  INTERACTIVE DIRECTORY SELECTION FAILED');
          _logger.warning(
            'Interactive selecting input dir crashed...\n'
            "It looks like you're running headless/on Synology/NAS...\n"
            "If so, you have to use cli options - run 'gpth --help' to see them",
          );
          _logger.warning('');
          _logger.warning('Please restart the program with CLI options instead.');
          _logger.error('No input directory could be selected');
          exit(2);
        }
        print('');
        
        final out = await ServiceContainer.instance.interactiveService.selectOutputDirectory();
        outputPath = out.path;
        print('');
      }
      
      inputPath = inDir.path;
    }
    
    // Validate paths
    if (inputPath == null || inputPath.isEmpty) {
      throw Exception('Input path is required. Use --input or run in interactive mode.');
    }
    
    if (outputPath == null || outputPath.isEmpty) {
      throw Exception('Output path is required. Use --output or run in interactive mode.');
    }
    
    // Handle input path resolution
    final resolvedInputPath = await TakeoutPathResolverService.resolveTakeoutPath(inputPath);
    
    return InputOutputPaths(
      inputPath: resolvedInputPath,
      outputPath: outputPath,
    );
  }
  
  /// Execute processing using the core API
  Future<ProcessingResult> _executeProcessing(ProcessingConfig config) async {
    if (config.verbose) {
      print('\n=== Starting Google Photos Takeout Helper Processing ===');
      print('Using Core API for processing...');
    }
    
    return await GpthCoreApi.instance.processGooglePhotos(config);
  }
  
  /// Show final processing results
  void _showResults(ProcessingConfig config, ProcessingResult result) {
    print('\n${"=" * 80}');
    if (result.isSuccess) {
      print(result.summary);
      
      if (config.verbose && enableProgressReporting) {
        print('\n${result.timingDetails}');
      }
    } else {
      print('Processing failed: ${result.error}');
    }
    print("=" * 80);
  }
}

/// Input/Output paths container
class InputOutputPaths {
  const InputOutputPaths({
    required this.inputPath,
    required this.outputPath,
  });
  
  final String inputPath;
  final String outputPath;
}