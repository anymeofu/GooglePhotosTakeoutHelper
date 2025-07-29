import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/gpth_core_api.dart';
import '../providers/app_state_provider.dart';
import '../theme/app_theme.dart';

class ValidationStatusCard extends ConsumerWidget {
  const ValidationStatusCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final inputPath = ref.watch(inputPathProvider);
    final validationResult = ref.watch(validationResultProvider);
    final spaceEstimate = ref.watch(spaceEstimateProvider);

    if (inputPath == null) {
      return const SizedBox.shrink();
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Icon(
                  validationResult?.isValid == true 
                    ? Icons.check_circle 
                    : Icons.warning,
                  color: validationResult?.isValid == true 
                    ? AppTheme.successColor 
                    : AppTheme.warningColor,
                ),
                const SizedBox(width: 8),
                Text(
                  'Directory Validation',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ],
            ),
            const SizedBox(height: 16),

            if (validationResult == null)
              const _LoadingValidation()
            else if (validationResult.isValid)
              _ValidDirectoryContent(
                validationResult: validationResult,
                spaceEstimate: spaceEstimate,
              )
            else
              _InvalidDirectoryContent(validationResult: validationResult),
          ],
        ),
      ),
    );
  }
}

class _LoadingValidation extends StatelessWidget {
  const _LoadingValidation();

  @override
  Widget build(BuildContext context) {
    return const Row(
      children: [
        SizedBox(
          width: 20,
          height: 20,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
        SizedBox(width: 12),
        Text('Validating directory structure...'),
      ],
    );
  }
}

class _ValidDirectoryContent extends StatelessWidget {
  const _ValidDirectoryContent({
    required this.validationResult,
    required this.spaceEstimate,
  });

  final ValidationResult validationResult;
  final SpaceEstimate? spaceEstimate;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Success indicator
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppTheme.successColor.withOpacity(0.1),
            border: Border.all(color: AppTheme.successColor.withOpacity(0.3)),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            children: [
              Icon(
                Icons.check_circle,
                color: AppTheme.successColor,
                size: 20,
              ),
              const SizedBox(width: 8),
              const Text(
                'Valid Google Photos Takeout detected!',
                style: TextStyle(fontWeight: FontWeight.w500),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // Validation details
        Text(
          'Structure Details',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        ...validationResult.details.map((detail) => Padding(
          padding: const EdgeInsets.only(bottom: 4),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                Icons.info_outline,
                size: 16,
                color: Colors.grey[600],
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  detail,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ),
            ],
          ),
        )),

        if (spaceEstimate != null) ...[
          const SizedBox(height: 16),
          const Divider(),
          const SizedBox(height: 12),
          _SpaceEstimateSection(spaceEstimate: spaceEstimate!),
        ],
      ],
    );
  }
}

class _InvalidDirectoryContent extends StatelessWidget {
  const _InvalidDirectoryContent({required this.validationResult});

  final ValidationResult validationResult;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Error indicator
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppTheme.warningColor.withOpacity(0.1),
            border: Border.all(color: AppTheme.warningColor.withOpacity(0.3)),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    Icons.warning,
                    color: AppTheme.warningColor,
                    size: 20,
                  ),
                  const SizedBox(width: 8),
                  const Text(
                    'Directory validation issues',
                    style: TextStyle(fontWeight: FontWeight.w500),
                  ),
                ],
              ),
              if (validationResult.message.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(
                  validationResult.message,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 16),

        // Validation details
        if (validationResult.details.isNotEmpty) ...[
          Text(
            'Issues Found',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          ...validationResult.details.map((detail) => Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  Icons.error_outline,
                  size: 16,
                  color: AppTheme.warningColor,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    detail,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ),
              ],
            ),
          )),
          const SizedBox(height: 16),
        ],

        // Troubleshooting tips
        _TroubleshootingTips(),
      ],
    );
  }
}

class _SpaceEstimateSection extends StatelessWidget {
  const _SpaceEstimateSection({required this.spaceEstimate});

  final SpaceEstimate spaceEstimate;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Space Estimate',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        
        _SpaceItem(
          icon: Icons.storage,
          label: 'Current Size',
          value: _formatBytes(spaceEstimate.currentSize),
          color: Colors.blue,
        ),
        _SpaceItem(
          icon: Icons.trending_up,
          label: 'Estimated Required',
          value: _formatBytes(spaceEstimate.estimatedRequiredSpace),
          color: AppTheme.warningColor,
        ),
        if (spaceEstimate.additionalSpaceNeeded > 0)
          _SpaceItem(
            icon: Icons.add,
            label: 'Additional Needed',
            value: _formatBytes(spaceEstimate.additionalSpaceNeeded),
            color: AppTheme.errorColor,
          ),
        _SpaceItem(
          icon: Icons.assessment,
          label: 'Space Multiplier',
          value: '${spaceEstimate.spaceMultiplier.toStringAsFixed(1)}x',
          color: Colors.grey,
        ),
      ],
    );
  }

  String _formatBytes(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    if (bytes < 1024 * 1024 * 1024) return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
    return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB';
  }
}

class _SpaceItem extends StatelessWidget {
  const _SpaceItem({
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
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 8),
          Text(
            '$label:',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const Spacer(),
          Text(
            value,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w500,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}

class _TroubleshootingTips extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.blue.withOpacity(0.1),
        border: Border.all(color: Colors.blue.withOpacity(0.3)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.lightbulb_outline,
                color: Colors.blue,
                size: 20,
              ),
              const SizedBox(width: 8),
              Text(
                'Troubleshooting Tips',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          const Text(
            '• Ensure you have extracted all ZIP files to the same directory\n'
            '• Look for "Photos from YYYY" folders in your directory\n'
            '• Make sure all ZIP files were extracted completely\n'
            '• Check that the directory contains a valid Takeout structure',
            style: TextStyle(fontSize: 13),
          ),
        ],
      ),
    );
  }
}