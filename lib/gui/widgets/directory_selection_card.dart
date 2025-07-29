import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/app_state_provider.dart';
import '../theme/app_theme.dart';

class DirectorySelectionCard extends ConsumerWidget {
  const DirectorySelectionCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final inputPath = ref.watch(inputPathProvider);
    final outputPath = ref.watch(outputPathProvider);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Icon(
                  Icons.folder_open,
                  color: AppTheme.primaryColor,
                ),
                const SizedBox(width: 8),
                Text(
                  'Directory Selection',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Input Directory
            _DirectoryField(
              label: 'Input Directory',
              subtitle: 'Select the folder containing your extracted Google Photos Takeout',
              path: inputPath,
              onPathSelected: (path) {
                ref.read(appStateProvider.notifier).setInputPath(path);
              },
              icon: Icons.input,
              iconColor: Colors.blue,
            ),
            const SizedBox(height: 16),

            // Output Directory
            _DirectoryField(
              label: 'Output Directory', 
              subtitle: 'Select where you want your organized photos to be saved',
              path: outputPath,
              onPathSelected: (path) {
                ref.read(appStateProvider.notifier).setOutputPath(path);
              },
              icon: Icons.output,
              iconColor: Colors.green,
            ),

            if (inputPath != null || outputPath != null) ...[
              const SizedBox(height: 12),
              const Divider(),
              const SizedBox(height: 8),
              _buildPathSummary(context, inputPath, outputPath),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildPathSummary(BuildContext context, String? inputPath, String? outputPath) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Selected Paths',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        if (inputPath != null)
          _PathDisplay(
            label: 'Input:',
            path: inputPath,
            icon: Icons.folder,
            iconColor: Colors.blue,
          ),
        if (outputPath != null)
          _PathDisplay(
            label: 'Output:',
            path: outputPath,
            icon: Icons.folder,
            iconColor: Colors.green,
          ),
      ],
    );
  }
}

class _DirectoryField extends StatelessWidget {
  const _DirectoryField({
    required this.label,
    required this.subtitle,
    required this.path,
    required this.onPathSelected,
    required this.icon,
    required this.iconColor,
  });

  final String label;
  final String subtitle;
  final String? path;
  final ValueChanged<String> onPathSelected;
  final IconData icon;
  final Color iconColor;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Icon(icon, color: iconColor, size: 20),
            const SizedBox(width: 8),
            Text(
              label,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const Spacer(),
            OutlinedButton.icon(
              onPressed: _selectDirectory,
              icon: const Icon(Icons.folder_open, size: 20),
              label: Text(path == null ? 'Select' : 'Change'),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          subtitle,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: Colors.grey[600],
          ),
        ),
        if (path != null) ...[
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.grey[100],
              border: Border.all(color: Colors.grey[300]!),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Row(
              children: [
                Icon(Icons.folder, color: iconColor, size: 16),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    path!,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      fontFamily: 'monospace',
                    ),
                    overflow: TextOverflow.ellipsis,
                    maxLines: 2,
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.clear, size: 16),
                  onPressed: () => onPathSelected(''),
                  tooltip: 'Clear selection',
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }

  Future<void> _selectDirectory() async {
    try {
      final String? selectedDirectory = await FilePicker.platform.getDirectoryPath(
        dialogTitle: 'Select $label',
      );

      if (selectedDirectory != null) {
        onPathSelected(selectedDirectory);
      }
    } catch (e) {
      // Handle error - could show a snackbar or dialog
      debugPrint('Error selecting directory: $e');
    }
  }
}

class _PathDisplay extends StatelessWidget {
  const _PathDisplay({
    required this.label,
    required this.path,
    required this.icon,
    required this.iconColor,
  });

  final String label;
  final String path;
  final IconData icon;
  final Color iconColor;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: iconColor, size: 16),
          const SizedBox(width: 8),
          Text(
            label,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              path,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                fontFamily: 'monospace',
              ),
              overflow: TextOverflow.ellipsis,
              maxLines: 1,
            ),
          ),
        ],
      ),
    );
  }
}