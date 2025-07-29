import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../domain/models/processing_config_model.dart';
import '../providers/app_state_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/directory_selection_card.dart';
import '../widgets/validation_status_card.dart';
import '../widgets/configuration_card.dart';
import '../widgets/processing_options_card.dart';
import '../widgets/exif_tool_status_card.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  // Configuration state
  AlbumBehavior _albumBehavior = AlbumBehavior.shortcut;
  DateDivisionLevel _dateDivision = DateDivisionLevel.none;
  bool _writeExif = true;
  bool _skipExtras = false;
  bool _guessFromName = true;
  ExtensionFixingMode _extensionFixing = ExtensionFixingMode.standard;
  bool _transformPixelMp = false;
  bool _updateCreationTime = false;
  bool _limitFileSize = false;
  bool _dividePartnerShared = false;

  @override
  void initState() {
    super.initState();
    // Initialize the GPTH core API when the app starts
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(appStateProvider.notifier).initialize();
    });
  }

  @override
  Widget build(BuildContext context) {
    final appState = ref.watch(appStateProvider);
    final isInitialized = ref.watch(isInitializedProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Google Photos Takeout Helper'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: isInitialized ? _refreshStatus : null,
            tooltip: 'Refresh Status',
          ),
        ],
      ),
      body: !isInitialized
          ? const _LoadingView()
          : appState.error != null
              ? _ErrorView(error: appState.error!)
              : _MainView(
                  albumBehavior: _albumBehavior,
                  dateDivision: _dateDivision,
                  writeExif: _writeExif,
                  skipExtras: _skipExtras,
                  guessFromName: _guessFromName,
                  extensionFixing: _extensionFixing,
                  transformPixelMp: _transformPixelMp,
                  updateCreationTime: _updateCreationTime,
                  limitFileSize: _limitFileSize,
                  dividePartnerShared: _dividePartnerShared,
                  onAlbumBehaviorChanged: (value) {
                    setState(() => _albumBehavior = value);
                    ref.read(appStateProvider.notifier).updateSpaceEstimate(value);
                  },
                  onDateDivisionChanged: (value) => setState(() => _dateDivision = value),
                  onWriteExifChanged: (value) => setState(() => _writeExif = value),
                  onSkipExtrasChanged: (value) => setState(() => _skipExtras = value),
                  onGuessFromNameChanged: (value) => setState(() => _guessFromName = value),
                  onExtensionFixingChanged: (value) => setState(() => _extensionFixing = value),
                  onTransformPixelMpChanged: (value) => setState(() => _transformPixelMp = value),
                  onUpdateCreationTimeChanged: (value) => setState(() => _updateCreationTime = value),
                  onLimitFileSizeChanged: (value) => setState(() => _limitFileSize = value),
                  onDividePartnerSharedChanged: (value) => setState(() => _dividePartnerShared = value),
                  onStartProcessing: _startProcessing,
                ),
      floatingActionButton: _buildFloatingActionButton(context),
    );
  }

  Widget? _buildFloatingActionButton(BuildContext context) {
    final inputPath = ref.watch(inputPathProvider);
    final outputPath = ref.watch(outputPathProvider);
    final validationResult = ref.watch(validationResultProvider);
    final isProcessing = ref.watch(isProcessingProvider);

    final canProcess = inputPath != null &&
        outputPath != null &&
        validationResult?.isValid == true &&
        !isProcessing;

    if (!canProcess) return null;

    return FloatingActionButton.extended(
      onPressed: _startProcessing,
      backgroundColor: AppTheme.successColor,
      icon: const Icon(Icons.play_arrow),
      label: const Text('Start Processing'),
    );
  }

  Future<void> _refreshStatus() async {
    await ref.read(appStateProvider.notifier).initialize();
  }

  Future<void> _startProcessing() async {
    final inputPath = ref.read(inputPathProvider);
    final outputPath = ref.read(outputPathProvider);

    if (inputPath == null || outputPath == null) {
      _showSnackBar('Please select input and output directories');
      return;
    }

    final config = ProcessingConfig(
      inputPath: inputPath,
      outputPath: outputPath,
      albumBehavior: _albumBehavior,
      dateDivision: _dateDivision,
      writeExif: _writeExif,
      skipExtras: _skipExtras,
      guessFromName: _guessFromName,
      extensionFixing: _extensionFixing,
      transformPixelMp: _transformPixelMp,
      updateCreationTime: _updateCreationTime,
      limitFileSize: _limitFileSize,
      dividePartnerShared: _dividePartnerShared,
    );

    // Navigate to processing screen
    context.push('/processing', extra: {'config': config});
  }

  void _showSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }
}

class _LoadingView extends StatelessWidget {
  const _LoadingView();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(),
          SizedBox(height: 16),
          Text('Initializing GPTH...'),
          SizedBox(height: 8),
          Text(
            'Checking ExifTool and setting up services',
            style: TextStyle(color: Colors.grey),
          ),
        ],
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.error});

  final String error;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.error_outline,
            size: 64,
            color: AppTheme.errorColor,
          ),
          const SizedBox(height: 16),
          Text(
            'Initialization Failed',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 32),
            child: Text(
              error,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.grey),
            ),
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: () {
              // Try to initialize again
              context.findAncestorStateOfType<ConsumerState>()
                  ?.ref.read(appStateProvider.notifier).initialize();
            },
            icon: const Icon(Icons.refresh),
            label: const Text('Retry'),
          ),
        ],
      ),
    );
  }
}

class _MainView extends StatelessWidget {
  const _MainView({
    required this.albumBehavior,
    required this.dateDivision,
    required this.writeExif,
    required this.skipExtras,
    required this.guessFromName,
    required this.extensionFixing,
    required this.transformPixelMp,
    required this.updateCreationTime,
    required this.limitFileSize,
    required this.dividePartnerShared,
    required this.onAlbumBehaviorChanged,
    required this.onDateDivisionChanged,
    required this.onWriteExifChanged,
    required this.onSkipExtrasChanged,
    required this.onGuessFromNameChanged,
    required this.onExtensionFixingChanged,
    required this.onTransformPixelMpChanged,
    required this.onUpdateCreationTimeChanged,
    required this.onLimitFileSizeChanged,
    required this.onDividePartnerSharedChanged,
    required this.onStartProcessing,
  });

  final AlbumBehavior albumBehavior;
  final DateDivisionLevel dateDivision;
  final bool writeExif;
  final bool skipExtras;
  final bool guessFromName;
  final ExtensionFixingMode extensionFixing;
  final bool transformPixelMp;
  final bool updateCreationTime;
  final bool limitFileSize;
  final bool dividePartnerShared;
  final ValueChanged<AlbumBehavior> onAlbumBehaviorChanged;
  final ValueChanged<DateDivisionLevel> onDateDivisionChanged;
  final ValueChanged<bool> onWriteExifChanged;
  final ValueChanged<bool> onSkipExtrasChanged;
  final ValueChanged<bool> onGuessFromNameChanged;
  final ValueChanged<ExtensionFixingMode> onExtensionFixingChanged;
  final ValueChanged<bool> onTransformPixelMpChanged;
  final ValueChanged<bool> onUpdateCreationTimeChanged;
  final ValueChanged<bool> onLimitFileSizeChanged;
  final ValueChanged<bool> onDividePartnerSharedChanged;
  final VoidCallback onStartProcessing;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Welcome message
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  Icon(
                    Icons.photo_library,
                    size: 48,
                    color: AppTheme.primaryColor,
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Welcome to Google Photos Takeout Helper',
                    style: Theme.of(context).textTheme.headlineSmall,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Organize your Google Photos Takeout into a clean, chronological structure with album support.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.grey),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // ExifTool Status
          const ExifToolStatusCard(),
          const SizedBox(height: 16),

          // Directory Selection
          const DirectorySelectionCard(),
          const SizedBox(height: 16),

          // Validation Status
          const ValidationStatusCard(),
          const SizedBox(height: 16),

          // Configuration
          ConfigurationCard(
            albumBehavior: albumBehavior,
            dateDivision: dateDivision,
            onAlbumBehaviorChanged: onAlbumBehaviorChanged,
            onDateDivisionChanged: onDateDivisionChanged,
          ),
          const SizedBox(height: 16),

          // Processing Options
          ProcessingOptionsCard(
            writeExif: writeExif,
            skipExtras: skipExtras,
            guessFromName: guessFromName,
            extensionFixing: extensionFixing,
            transformPixelMp: transformPixelMp,
            updateCreationTime: updateCreationTime,
            limitFileSize: limitFileSize,
            dividePartnerShared: dividePartnerShared,
            onWriteExifChanged: onWriteExifChanged,
            onSkipExtrasChanged: onSkipExtrasChanged,
            onGuessFromNameChanged: onGuessFromNameChanged,
            onExtensionFixingChanged: onExtensionFixingChanged,
            onTransformPixelMpChanged: onTransformPixelMpChanged,
            onUpdateCreationTimeChanged: onUpdateCreationTimeChanged,
            onLimitFileSizeChanged: onLimitFileSizeChanged,
            onDividePartnerSharedChanged: onDividePartnerSharedChanged,
          ),
        ],
      ),
    );
  }
}