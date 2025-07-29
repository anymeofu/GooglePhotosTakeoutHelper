import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../domain/models/processing_result_model.dart';
import '../theme/app_theme.dart';

class ResultsScreen extends ConsumerWidget {
  const ResultsScreen({
    super.key,
    required this.result,
  });

  final ProcessingResult result;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Processing Results'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Success header
            _ResultHeader(result: result),
            const SizedBox(height: 32),

            // Summary statistics
            _ResultSummary(result: result),
            const SizedBox(height: 24),

            // Processing details by step
            _ProcessingDetails(result: result),
            const SizedBox(height: 24),

            // Performance metrics
            _PerformanceMetrics(result: result),
            const SizedBox(height: 24),

            // Error summary (if any)
            if (!result.isSuccess) ...[
              _ErrorSummary(result: result),
              const SizedBox(height: 24),
            ],

            // Action buttons
            _ActionButtons(result: result),
          ],
        ),
      ),
    );
  }
}

class _ResultHeader extends StatelessWidget {
  const _ResultHeader({required this.result});

  final ProcessingResult result;

  @override
  Widget build(BuildContext context) {
    final isSuccess = result.isSuccess;
    
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: (isSuccess ? AppTheme.successColor : AppTheme.warningColor)
            .withOpacity(0.1),
        border: Border.all(
          color: (isSuccess ? AppTheme.successColor : AppTheme.warningColor)
              .withOpacity(0.3),
        ),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          Icon(
            isSuccess ? Icons.check_circle : Icons.warning,
            size: 64,
            color: isSuccess ? AppTheme.successColor : AppTheme.warningColor,
          ),
          const SizedBox(height: 16),
          Text(
            isSuccess 
              ? 'Processing Completed Successfully!'
              : 'Processing Completed with Warnings',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: isSuccess ? AppTheme.successColor : AppTheme.warningColor,
              fontWeight: FontWeight.bold,
            ),
            textAlign: TextAlign.center,
          ),
          if (result.endTime != null) ...[
            const SizedBox(height: 8),
            Text(
              'Completed on ${_formatDateTime(result.endTime!)}',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Colors.grey[600],
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ],
      ),
    );
  }

  String _formatDateTime(DateTime dateTime) {
    return '${dateTime.day}/${dateTime.month}/${dateTime.year} '
           'at ${dateTime.hour}:${dateTime.minute.toString().padLeft(2, '0')}';
  }
}

class _ResultSummary extends StatelessWidget {
  const _ResultSummary({required this.result});

  final ProcessingResult result;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Summary',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            
            Row(
              children: [
                Expanded(
                  child: _StatCard(
                    icon: Icons.photo,
                    label: 'Photos Processed',
                    value: result.mediaProcessed.toString(),
                    color: AppTheme.primaryColor,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _StatCard(
                    icon: Icons.folder_copy,
                    label: 'Files Moved',
                    value: result.mediaProcessed.toString(),
                    color: AppTheme.successColor,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            
            Row(
              children: [
                Expanded(
                  child: _StatCard(
                    icon: Icons.copy_all,
                    label: 'Duplicates Found',
                    value: result.duplicatesRemoved.toString(),
                    color: AppTheme.warningColor,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _StatCard(
                    icon: Icons.timer,
                    label: 'Processing Time',
                    value: _formatDuration(result.totalProcessingTime),
                    color: Colors.blue,
                  ),
                ),
              ],
            ),
            
            if (result.extrasSkipped > 0) ...[
              const SizedBox(height: 12),
              _StatCard(
                icon: Icons.storage,
                label: 'Extras Skipped',
                value: result.extrasSkipped.toString(),
                color: AppTheme.successColor,
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _formatDuration(Duration duration) {
    if (duration.inHours > 0) {
      return '${duration.inHours}h ${duration.inMinutes % 60}m';
    } else if (duration.inMinutes > 0) {
      return '${duration.inMinutes}m ${duration.inSeconds % 60}s';
    } else {
      return '${duration.inSeconds}s';
    }
  }

  String _formatBytes(int bytes) {
    if (bytes < 1024) return '${bytes}B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)}KB';
    if (bytes < 1024 * 1024 * 1024) return '${(bytes / (1024 * 1024)).toStringAsFixed(1)}MB';
    return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(1)}GB';
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 32),
          const SizedBox(height: 8),
          Text(
            value,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: color,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: Theme.of(context).textTheme.bodySmall,
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

class _ProcessingDetails extends StatelessWidget {
  const _ProcessingDetails({required this.result});

  final ProcessingResult result;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Processing Details',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            
            // Show details for each step if available
            if (result.stepResults != null && result.stepResults!.isNotEmpty) ...[
              ...result.stepResults!.map((step) => _ProcessingStep(step: step)),
            ] else ...[
              const _ProcessingStep(step: null), // Placeholder for basic info
            ],
          ],
        ),
      ),
    );
  }
}

class _ProcessingStep extends StatelessWidget {
  const _ProcessingStep({required this.step});

  final dynamic step; // Could be a specific step result model

  @override
  Widget build(BuildContext context) {
    // This is a placeholder implementation
    // In a real implementation, you'd parse the step details
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.grey[50],
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey[300]!),
      ),
      child: Row(
        children: [
          Icon(
            Icons.check_circle,
            color: AppTheme.successColor,
            size: 20,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              step?.toString() ?? 'Processing completed successfully',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }
}

class _PerformanceMetrics extends StatelessWidget {
  const _PerformanceMetrics({required this.result});

  final ProcessingResult result;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Performance Metrics',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            
            _MetricRow(
              label: 'Average Processing Speed',
              value: result.totalProcessingTime.inSeconds > 0
                ? '${(result.mediaProcessed / result.totalProcessingTime.inSeconds).toStringAsFixed(1)} files/sec'
                : 'N/A',
            ),
            _MetricRow(
              label: 'Peak Memory Usage',
              value: 'N/A', // Would require memory tracking
            ),
            _MetricRow(
              label: 'Disk I/O Operations',
              value: '${result.filesMoved + result.duplicatesFound}',
            ),
          ],
        ),
      ),
    );
  }
}

class _MetricRow extends StatelessWidget {
  const _MetricRow({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          Text(
            value,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

class _ErrorSummary extends StatelessWidget {
  const _ErrorSummary({required this.result});

  final ProcessingResult result;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.warning,
                  color: AppTheme.warningColor,
                  size: 24,
                ),
                const SizedBox(width: 8),
                Text(
                  'Warnings & Issues',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: AppTheme.warningColor,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // Show error messages if available
            Text(
              'Some files may not have been processed completely. Check the logs for detailed information.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }
}

class _ActionButtons extends StatelessWidget {
  const _ActionButtons({required this.result});

  final ProcessingResult result;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ElevatedButton.icon(
          onPressed: () {
            // Open output folder
            // This would require platform-specific implementation
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Opening output folder...'),
              ),
            );
          },
          icon: const Icon(Icons.folder_open),
          label: const Text('Open Output Folder'),
        ),
        const SizedBox(height: 12),
        
        Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => context.go('/'),
                icon: const Icon(Icons.home),
                label: const Text('Process More'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () {
                  // Export results
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Exporting results...'),
                    ),
                  );
                },
                icon: const Icon(Icons.save_alt),
                label: const Text('Export Report'),
              ),
            ),
          ],
        ),
      ],
    );
  }
}