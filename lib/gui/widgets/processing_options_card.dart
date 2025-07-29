import 'dart:io';

import 'package:flutter/material.dart';

import '../../domain/models/processing_config_model.dart';
import '../theme/app_theme.dart';

class ProcessingOptionsCard extends StatelessWidget {
  const ProcessingOptionsCard({
    super.key,
    required this.writeExif,
    required this.skipExtras,
    required this.guessFromName,
    required this.extensionFixing,
    required this.transformPixelMp,
    required this.updateCreationTime,
    required this.limitFileSize,
    required this.dividePartnerShared,
    required this.onWriteExifChanged,
    required this.onSkipExtrasChanged,
    required this.onGuessFromNameChanged,
    required this.onExtensionFixingChanged,
    required this.onTransformPixelMpChanged,
    required this.onUpdateCreationTimeChanged,
    required this.onLimitFileSizeChanged,
    required this.onDividePartnerSharedChanged,
  });

  final bool writeExif;
  final bool skipExtras;
  final bool guessFromName;
  final ExtensionFixingMode extensionFixing;
  final bool transformPixelMp;
  final bool updateCreationTime;
  final bool limitFileSize;
  final bool dividePartnerShared;
  final ValueChanged<bool> onWriteExifChanged;
  final ValueChanged<bool> onSkipExtrasChanged;
  final ValueChanged<bool> onGuessFromNameChanged;
  final ValueChanged<ExtensionFixingMode> onExtensionFixingChanged;
  final ValueChanged<bool> onTransformPixelMpChanged;
  final ValueChanged<bool> onUpdateCreationTimeChanged;
  final ValueChanged<bool> onLimitFileSizeChanged;
  final ValueChanged<bool> onDividePartnerSharedChanged;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Icon(
                  Icons.tune,
                  color: AppTheme.primaryColor,
                ),
                const SizedBox(width: 8),
                Text(
                  'Processing Options',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Metadata Options Section
            _SectionHeader(
              icon: Icons.info,
              title: 'Metadata & EXIF',
              color: Colors.blue,
            ),
            const SizedBox(height: 12),
            _BooleanOption(
              title: 'Write EXIF Data',
              description: 'Embed dates and GPS coordinates into image files (requires ExifTool for best results)',
              value: writeExif,
              onChanged: onWriteExifChanged,
              icon: Icons.date_range,
            ),
            _BooleanOption(
              title: 'Guess Dates from Filenames',
              description: 'Try to extract dates from filenames when metadata is missing',
              value: guessFromName,
              onChanged: onGuessFromNameChanged,
              icon: Icons.text_fields,
            ),

            const SizedBox(height: 20),

            // File Processing Section
            _SectionHeader(
              icon: Icons.file_present,
              title: 'File Processing',
              color: Colors.green,
            ),
            const SizedBox(height: 12),
            
            // Extension Fixing Dropdown
            _ExtensionFixingOption(
              extensionFixing: extensionFixing,
              onExtensionFixingChanged: onExtensionFixingChanged,
            ),
            
            _BooleanOption(
              title: 'Skip Extra Files',
              description: 'Skip files like *-edited.jpg, *-EFFECTS.jpg that are processed versions',
              value: skipExtras,
              onChanged: onSkipExtrasChanged,
              icon: Icons.filter_alt_off,
            ),
            _BooleanOption(
              title: 'Transform Pixel Motion Photos',
              description: 'Convert .MP/.MV files to .mp4 for better compatibility',
              value: transformPixelMp,
              onChanged: onTransformPixelMpChanged,
              icon: Icons.transform,
            ),

            const SizedBox(height: 20),

            // System Options Section
            _SectionHeader(
              icon: Icons.computer,
              title: 'System Options',
              color: Colors.orange,
            ),
            const SizedBox(height: 12),
            _BooleanOption(
              title: 'Limit File Size (64MB)',
              description: 'Skip very large files to prevent memory issues on low-RAM systems',
              value: limitFileSize,
              onChanged: onLimitFileSizeChanged,
              icon: Icons.memory,
            ),
            if (Platform.isWindows)
              _BooleanOption(
                title: 'Update Creation Time',
                description: 'Sync file creation time with modification time (Windows only)',
                value: updateCreationTime,
                onChanged: onUpdateCreationTimeChanged,
                icon: Icons.schedule,
              ),

            const SizedBox(height: 20),

            // Partner Sharing Section
            _SectionHeader(
              icon: Icons.people,
              title: 'Partner Sharing',
              color: Colors.purple,
            ),
            const SizedBox(height: 12),
            _BooleanOption(
              title: 'Separate Partner Shared Media',
              description: 'Move partner shared photos to a separate PARTNER_SHARED folder',
              value: dividePartnerShared,
              onChanged: onDividePartnerSharedChanged,
              icon: Icons.share,
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({
    required this.icon,
    required this.title,
    required this.color,
  });

  final IconData icon;
  final String title;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, color: color, size: 20),
        const SizedBox(width: 8),
        Text(
          title,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            color: color,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}

class _BooleanOption extends StatelessWidget {
  const _BooleanOption({
    required this.title,
    required this.description,
    required this.value,
    required this.onChanged,
    required this.icon,
  });

  final String title;
  final String description;
  final bool value;
  final ValueChanged<bool> onChanged;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        onTap: () => onChanged(!value),
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.all(8),
          child: Row(
            children: [
              Icon(icon, size: 20, color: Colors.grey[600]),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
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
              const SizedBox(width: 8),
              Switch(
                value: value,
                onChanged: onChanged,
                activeColor: AppTheme.primaryColor,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ExtensionFixingOption extends StatelessWidget {
  const _ExtensionFixingOption({
    required this.extensionFixing,
    required this.onExtensionFixingChanged,
  });

  final ExtensionFixingMode extensionFixing;
  final ValueChanged<ExtensionFixingMode> onExtensionFixingChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(8),
      child: Row(
        children: [
          Icon(Icons.extension, size: 20, color: Colors.grey[600]),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Fix File Extensions',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'Correct mismatched file extensions (e.g., HEIC files saved as .jpg)',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey[600],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          DropdownButton<ExtensionFixingMode>(
            value: extensionFixing,
            onChanged: (value) => onExtensionFixingChanged(value!),
            items: ExtensionFixingMode.values.map((mode) {
              return DropdownMenuItem(
                value: mode,
                child: Text(_getExtensionFixingLabel(mode)),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  String _getExtensionFixingLabel(ExtensionFixingMode mode) {
    switch (mode) {
      case ExtensionFixingMode.none:
        return 'None';
      case ExtensionFixingMode.standard:
        return 'Standard';
      case ExtensionFixingMode.conservative:
        return 'Conservative';
      case ExtensionFixingMode.solo:
        return 'Solo Mode';
    }
  }
}