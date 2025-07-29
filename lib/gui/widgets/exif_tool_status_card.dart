import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/gpth_core_api.dart';
import '../providers/app_state_provider.dart';
import '../theme/app_theme.dart';

class ExifToolStatusCard extends ConsumerWidget {
  const ExifToolStatusCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final exifToolInfo = ref.watch(exifToolInfoProvider);

    if (exifToolInfo == null) {
      return const _LoadingCard();
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
                  Icons.build,
                  color: exifToolInfo.isAvailable 
                    ? AppTheme.successColor 
                    : AppTheme.warningColor,
                ),
                const SizedBox(width: 8),
                Text(
                  'ExifTool Status',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ],
            ),
            const SizedBox(height: 16),

            if (exifToolInfo.isAvailable)
              _AvailableStatus(exifToolInfo: exifToolInfo)
            else
              _NotAvailableStatus(exifToolInfo: exifToolInfo),
          ],
        ),
      ),
    );
  }
}

class _LoadingCard extends StatelessWidget {
  const _LoadingCard();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            const SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            const SizedBox(width: 12),
            Text(
              'Checking ExifTool availability...',
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ],
        ),
      ),
    );
  }
}

class _AvailableStatus extends StatelessWidget {
  const _AvailableStatus({required this.exifToolInfo});

  final ExifToolInfo exifToolInfo;

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
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'ExifTool is available!',
                      style: TextStyle(fontWeight: FontWeight.w500),
                    ),
                    if (exifToolInfo.version != null) ...[
                      const SizedBox(height: 4),
                      Text(
                        'Version: ${exifToolInfo.version}',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          fontFamily: 'monospace',
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // Features with ExifTool
        Text(
          'Enhanced Features Available',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        ...[
          _FeatureItem(
            icon: Icons.calendar_today,
            title: 'Enhanced Date Extraction',
            description: 'Extract dates from EXIF data in all image formats',
            isAvailable: true,
          ),
          _FeatureItem(
            icon: Icons.location_on,
            title: 'GPS Coordinate Writing',
            description: 'Embed GPS coordinates from Google Photos metadata',
            isAvailable: true,
          ),
          _FeatureItem(
            icon: Icons.edit,
            title: 'Metadata Writing',
            description: 'Write dates and locations to RAW and HEIC files',
            isAvailable: true,
          ),
          _FeatureItem(
            icon: Icons.camera,
            title: 'Camera Information',
            description: 'Preserve and enhance camera metadata',
            isAvailable: true,
          ),
        ],
      ],
    );
  }
}

class _NotAvailableStatus extends StatelessWidget {
  const _NotAvailableStatus({required this.exifToolInfo});

  final ExifToolInfo exifToolInfo;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Warning indicator
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppTheme.warningColor.withOpacity(0.1),
            border: Border.all(color: AppTheme.warningColor.withOpacity(0.3)),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            children: [
              Icon(
                Icons.warning,
                color: AppTheme.warningColor,
                size: 20,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'ExifTool not found',
                      style: TextStyle(fontWeight: FontWeight.w500),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      exifToolInfo.message,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // Limited features
        Text(
          'Limited Features (Basic Mode)',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        ...[
          _FeatureItem(
            icon: Icons.calendar_today,
            title: 'Basic Date Extraction',
            description: 'Extract dates from JSON files and basic EXIF (JPEG only)',
            isAvailable: true,
          ),
          _FeatureItem(
            icon: Icons.location_on,
            title: 'GPS Coordinate Writing',
            description: 'Limited to JPEG files only',
            isAvailable: false,
          ),
          _FeatureItem(
            icon: Icons.edit,
            title: 'Metadata Writing',
            description: 'Cannot write to RAW, HEIC, or other advanced formats',
            isAvailable: false,
          ),
          _FeatureItem(
            icon: Icons.camera,
            title: 'Camera Information',
            description: 'Limited metadata preservation',
            isAvailable: false,
          ),
        ],
        const SizedBox(height: 16),

        // Installation instructions
        _InstallationInstructions(),
      ],
    );
  }
}

class _FeatureItem extends StatelessWidget {
  const _FeatureItem({
    required this.icon,
    required this.title,
    required this.description,
    required this.isAvailable,
  });

  final IconData icon;
  final String title;
  final String description;
  final bool isAvailable;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            isAvailable ? Icons.check_circle : Icons.cancel,
            size: 16,
            color: isAvailable ? AppTheme.successColor : AppTheme.errorColor,
          ),
          const SizedBox(width: 8),
          Icon(
            icon,
            size: 16,
            color: Colors.grey[600],
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  description,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey[600],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _InstallationInstructions extends StatelessWidget {
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
                Icons.download,
                color: Colors.blue,
                size: 20,
              ),
              const SizedBox(width: 8),
              Text(
                'Install ExifTool for Best Results',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          const Text(
            'To get the most out of GPTH, install ExifTool:\n\n'
            '• Windows: Download from exiftool.org and add to PATH\n'
            '• macOS: brew install exiftool\n'
            '• Linux: sudo apt install libimage-exiftool-perl\n\n'
            'After installation, restart GPTH to enable enhanced features.',
            style: TextStyle(fontSize: 13),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () {
              // Could open the ExifTool website or show more detailed instructions
            },
            icon: const Icon(Icons.open_in_new, size: 16),
            label: const Text('Download ExifTool'),
            style: OutlinedButton.styleFrom(
              foregroundColor: Colors.blue,
            ),
          ),
        ],
      ),
    );
  }
}