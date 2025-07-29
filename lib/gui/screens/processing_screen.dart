import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:percent_indicator/linear_percent_indicator.dart';

import '../../domain/models/processing_config_model.dart';
import '../providers/app_state_provider.dart';
import '../theme/app_theme.dart';

class ProcessingScreen extends ConsumerStatefulWidget {
  const ProcessingScreen({
    super.key,
    required this.config,
  });

  final ProcessingConfig? config;

  @override
  ConsumerState<ProcessingScreen> createState() => _ProcessingScreenState();
}

class _ProcessingScreenState extends ConsumerState<ProcessingScreen>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    // Setup pulse animation for the processing indicator
    _pulseController = AnimationController(
      duration: const Duration(seconds: 2),
      vsync: this,
    );
    _pulseAnimation = Tween<double>(
      begin: 0.8,
      end: 1.2,
    ).animate(CurvedAnimation(
      parent: _pulseController,
      curve: Curves.easeInOut,
    ));

    // Start processing when the screen loads
    if (widget.config != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _startProcessing();
      });
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  void _startProcessing() {
    _pulseController.repeat(reverse: true);
    ref.read(appStateProvider.notifier).startProcessing(widget.config!);
  }

  @override
  Widget build(BuildContext context) {
    final isProcessing = ref.watch(isProcessingProvider);
    final progress = ref.watch(processingProgressProvider);
    final message = ref.watch(processingMessageProvider);
    final result = ref.watch(resultProvider);
    final error = ref.watch(errorProvider);

    // Navigate to results screen when processing is complete
    ref.listen(appStateProvider, (previous, current) {
      if (previous?.isProcessing == true && 
          current.isProcessing == false && 
          current.result != null) {
        context.push('/results', extra: {'result': current.result});
      }
    });

    return Scaffold(
      appBar: AppBar(
        title: const Text('Processing Photos'),
        leading: !isProcessing 
          ? IconButton(
              icon: const Icon(Icons.arrow_back),
              onPressed: () => context.pop(),
            )
          : null,
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Main processing status
            if (error != null)
              _ErrorView(error: error)
            else if (isProcessing)
              _ProcessingView(
                progress: progress,
                message: message,
                pulseAnimation: _pulseAnimation,
              )
            else if (result != null)
              _CompletedView()
            else
              _InitializingView(),

            const SizedBox(height: 32),

            // Configuration summary
            if (widget.config != null) ...[
              _ConfigurationSummary(config: widget.config!),
              const SizedBox(height: 24),
            ],

            // Action buttons
            _ActionButtons(
              isProcessing: isProcessing,
              hasError: error != null,
              hasResult: result != null,
              onCancel: () => context.pop(),
              onRetry: _startProcessing,
              onShowResults: () {
                if (result != null) {
                  context.push('/results', extra: {'result': result});
                }
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _ProcessingView extends StatelessWidget {
  const _ProcessingView({
    required this.progress,
    required this.message,
    required this.pulseAnimation,
  });

  final double progress;
  final String? message;
  final Animation<double> pulseAnimation;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Animated processing icon
        AnimatedBuilder(
          animation: pulseAnimation,
          builder: (context, child) {
            return Transform.scale(
              scale: pulseAnimation.value,
              child: Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  color: AppTheme.primaryColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(40),
                ),
                child: Icon(
                  Icons.photo_library,
                  size: 40,
                  color: AppTheme.primaryColor,
                ),
              ),
            );
          },
        ),
        const SizedBox(height: 24),

        // Processing message
        Text(
          'Processing Your Photos',
          style: Theme.of(context).textTheme.headlineSmall,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 8),
        if (message != null) ...[
          Text(
            message!,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
              color: Colors.grey[600],
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
        ],

        // Progress bar
        LinearPercentIndicator(
          width: 300,
          lineHeight: 8,
          percent: progress.clamp(0.0, 1.0),
          backgroundColor: Colors.grey[300],
          progressColor: AppTheme.primaryColor,
          barRadius: const Radius.circular(4),
          animation: true,
          animationDuration: 500,
        ),
        const SizedBox(height: 12),
        Text(
          '${(progress * 100).toStringAsFixed(0)}% Complete',
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: Colors.grey[600],
          ),
        ),
      ],
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.error});

  final String error;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          width: 80,
          height: 80,
          decoration: BoxDecoration(
            color: AppTheme.errorColor.withOpacity(0.1),
            borderRadius: BorderRadius.circular(40),
          ),
          child: Icon(
            Icons.error,
            size: 40,
            color: AppTheme.errorColor,
          ),
        ),
        const SizedBox(height: 24),
        Text(
          'Processing Failed',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
            color: AppTheme.errorColor,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppTheme.errorColor.withOpacity(0.1),
            border: Border.all(color: AppTheme.errorColor.withOpacity(0.3)),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            error,
            style: Theme.of(context).textTheme.bodyMedium,
            textAlign: TextAlign.center,
          ),
        ),
      ],
    );
  }
}

class _CompletedView extends StatelessWidget {
  const _CompletedView();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          width: 80,
          height: 80,
          decoration: BoxDecoration(
            color: AppTheme.successColor.withOpacity(0.1),
            borderRadius: BorderRadius.circular(40),
          ),
          child: Icon(
            Icons.check_circle,
            size: 40,
            color: AppTheme.successColor,
          ),
        ),
        const SizedBox(height: 24),
        Text(
          'Processing Complete!',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
            color: AppTheme.successColor,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 8),
        Text(
          'Your photos have been successfully organized',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            color: Colors.grey[600],
          ),
          textAlign: TextAlign.center,
        ),
      ],
    );
  }
}

class _InitializingView extends StatelessWidget {
  const _InitializingView();

  @override
  Widget build(BuildContext context) {
    return const Column(
      children: [
        CircularProgressIndicator(),
        SizedBox(height: 24),
        Text('Preparing to process...'),
      ],
    );
  }
}

class _ConfigurationSummary extends StatelessWidget {
  const _ConfigurationSummary({required this.config});

  final ProcessingConfig config;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Configuration Summary',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            _ConfigItem(
              label: 'Input Directory',
              value: config.inputPath,
            ),
            _ConfigItem(
              label: 'Output Directory', 
              value: config.outputPath,
            ),
            _ConfigItem(
              label: 'Album Behavior',
              value: _getAlbumBehaviorName(config.albumBehavior),
            ),
            _ConfigItem(
              label: 'Date Organization',
              value: _getDateDivisionName(config.dateDivision),
            ),
            if (config.writeExif)
              const _ConfigItem(
                label: 'EXIF Writing',
                value: 'Enabled',
              ),
            if (config.skipExtras)
              const _ConfigItem(
                label: 'Skip Extras',
                value: 'Enabled',
              ),
          ],
        ),
      ),
    );
  }

  String _getAlbumBehaviorName(AlbumBehavior behavior) {
    switch (behavior) {
      case AlbumBehavior.shortcut:
        return 'Shortcuts/Symlinks';
      case AlbumBehavior.duplicateCopy:
        return 'Duplicate Copies';
      case AlbumBehavior.json:
        return 'JSON Metadata';
      case AlbumBehavior.nothing:
        return 'Ignore Albums';
      case AlbumBehavior.reverseShortcut:
        return 'Reverse Shortcuts';
    }
  }

  String _getDateDivisionName(DateDivisionLevel level) {
    switch (level) {
      case DateDivisionLevel.none:
        return 'Single Folder';
      case DateDivisionLevel.year:
        return 'Year Folders';
      case DateDivisionLevel.month:
        return 'Year/Month Folders';
      case DateDivisionLevel.day:
        return 'Year/Month/Day Folders';
    }
  }
}

class _ConfigItem extends StatelessWidget {
  const _ConfigItem({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              '$label:',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: Theme.of(context).textTheme.bodyMedium,
              overflow: TextOverflow.ellipsis,
              maxLines: 2,
            ),
          ),
        ],
      ),
    );
  }
}

class _ActionButtons extends StatelessWidget {
  const _ActionButtons({
    required this.isProcessing,
    required this.hasError,
    required this.hasResult,
    required this.onCancel,
    required this.onRetry,
    required this.onShowResults,
  });

  final bool isProcessing;
  final bool hasError;
  final bool hasResult;
  final VoidCallback onCancel;
  final VoidCallback onRetry;
  final VoidCallback onShowResults;

  @override
  Widget build(BuildContext context) {
    if (isProcessing) {
      return OutlinedButton.icon(
        onPressed: onCancel,
        icon: const Icon(Icons.close),
        label: const Text('Cancel'),
      );
    }

    if (hasError) {
      return Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          OutlinedButton.icon(
            onPressed: onCancel,
            icon: const Icon(Icons.arrow_back),
            label: const Text('Back'),
          ),
          ElevatedButton.icon(
            onPressed: onRetry,
            icon: const Icon(Icons.refresh),
            label: const Text('Retry'),
          ),
        ],
      );
    }

    if (hasResult) {
      return Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          OutlinedButton.icon(
            onPressed: onCancel,
            icon: const Icon(Icons.home),
            label: const Text('Home'),
          ),
          ElevatedButton.icon(
            onPressed: onShowResults,
            icon: const Icon(Icons.assessment),
            label: const Text('View Results'),
          ),
        ],
      );
    }

    return OutlinedButton.icon(
      onPressed: onCancel,
      icon: const Icon(Icons.arrow_back),
      label: const Text('Back'),
    );
  }
}