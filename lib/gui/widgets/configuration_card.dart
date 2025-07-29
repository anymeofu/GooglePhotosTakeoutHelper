import 'package:flutter/material.dart';

import '../../domain/models/processing_config_model.dart';
import '../theme/app_theme.dart';

class ConfigurationCard extends StatelessWidget {
  const ConfigurationCard({
    super.key,
    required this.albumBehavior,
    required this.dateDivision,
    required this.onAlbumBehaviorChanged,
    required this.onDateDivisionChanged,
  });

  final AlbumBehavior albumBehavior;
  final DateDivisionLevel dateDivision;
  final ValueChanged<AlbumBehavior> onAlbumBehaviorChanged;
  final ValueChanged<DateDivisionLevel> onDateDivisionChanged;

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
                  Icons.settings,
                  color: AppTheme.primaryColor,
                ),
                const SizedBox(width: 8),
                Text(
                  'Organization Configuration',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Album Behavior Selection
            _AlbumBehaviorSection(
              albumBehavior: albumBehavior,
              onAlbumBehaviorChanged: onAlbumBehaviorChanged,
            ),
            const SizedBox(height: 24),

            // Date Division Selection
            _DateDivisionSection(
              dateDivision: dateDivision,
              onDateDivisionChanged: onDateDivisionChanged,
            ),
          ],
        ),
      ),
    );
  }
}

class _AlbumBehaviorSection extends StatelessWidget {
  const _AlbumBehaviorSection({
    required this.albumBehavior,
    required this.onAlbumBehaviorChanged,
  });

  final AlbumBehavior albumBehavior;
  final ValueChanged<AlbumBehavior> onAlbumBehaviorChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(
              Icons.photo_album,
              size: 20,
              color: Colors.purple,
            ),
            const SizedBox(width: 8),
            Text(
              'Album Organization',
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          'Choose how albums should be organized in your output folder',
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: Colors.grey[600],
          ),
        ),
        const SizedBox(height: 12),

        ...AlbumBehavior.values.map((behavior) {
          final isSelected = albumBehavior == behavior;
          return Container(
            margin: const EdgeInsets.only(bottom: 8),
            child: InkWell(
              onTap: () => onAlbumBehaviorChanged(behavior),
              borderRadius: BorderRadius.circular(8),
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  border: Border.all(
                    color: isSelected 
                      ? AppTheme.primaryColor 
                      : Colors.grey[300]!,
                    width: isSelected ? 2 : 1,
                  ),
                  borderRadius: BorderRadius.circular(8),
                  color: isSelected 
                    ? AppTheme.primaryColor.withOpacity(0.05)
                    : null,
                ),
                child: Row(
                  children: [
                    Radio<AlbumBehavior>(
                      value: behavior,
                      groupValue: albumBehavior,
                      onChanged: (value) => onAlbumBehaviorChanged(value!),
                      activeColor: AppTheme.primaryColor,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(
                                _getAlbumBehaviorTitle(behavior),
                                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                              if (behavior == AlbumBehavior.shortcut) ...[
                                const SizedBox(width: 8),
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 6,
                                    vertical: 2,
                                  ),
                                  decoration: BoxDecoration(
                                    color: AppTheme.successColor,
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: const Text(
                                    'RECOMMENDED',
                                    style: TextStyle(
                                      color: Colors.white,
                                      fontSize: 10,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                              ],
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(
                            _getAlbumBehaviorDescription(behavior),
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        }),
      ],
    );
  }

  String _getAlbumBehaviorTitle(AlbumBehavior behavior) {
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

  String _getAlbumBehaviorDescription(AlbumBehavior behavior) {
    switch (behavior) {
      case AlbumBehavior.shortcut:
        return 'Create album folders with shortcuts to photos in ALL_PHOTOS. Space efficient and compatible with most systems.';
      case AlbumBehavior.duplicateCopy:
        return 'Create album folders with actual copies of photos. Uses more disk space but works everywhere.';
      case AlbumBehavior.json:
        return 'Store all photos in ALL_PHOTOS and create a JSON file with album information. Most space efficient.';
      case AlbumBehavior.nothing:
        return 'Ignore album information and put all photos in date-organized folders only.';
      case AlbumBehavior.reverseShortcut:
        return 'Store photos in album folders with shortcuts in ALL_PHOTOS pointing to album locations.';
    }
  }
}

class _DateDivisionSection extends StatelessWidget {
  const _DateDivisionSection({
    required this.dateDivision,
    required this.onDateDivisionChanged,
  });

  final DateDivisionLevel dateDivision;
  final ValueChanged<DateDivisionLevel> onDateDivisionChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(
              Icons.date_range,
              size: 20,
              color: Colors.orange,
            ),
            const SizedBox(width: 8),
            Text(
              'Date Organization',
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          'Choose how photos should be organized by date within the ALL_PHOTOS folder',
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: Colors.grey[600],
          ),
        ),
        const SizedBox(height: 12),

        ...DateDivisionLevel.values.map((level) {
          final isSelected = dateDivision == level;
          return Container(
            margin: const EdgeInsets.only(bottom: 8),
            child: InkWell(
              onTap: () => onDateDivisionChanged(level),
              borderRadius: BorderRadius.circular(8),
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  border: Border.all(
                    color: isSelected 
                      ? AppTheme.primaryColor 
                      : Colors.grey[300]!,
                    width: isSelected ? 2 : 1,
                  ),
                  borderRadius: BorderRadius.circular(8),
                  color: isSelected 
                    ? AppTheme.primaryColor.withOpacity(0.05)
                    : null,
                ),
                child: Row(
                  children: [
                    Radio<DateDivisionLevel>(
                      value: level,
                      groupValue: dateDivision,
                      onChanged: (value) => onDateDivisionChanged(value!),
                      activeColor: AppTheme.primaryColor,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _getDateDivisionTitle(level),
                            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            _getDateDivisionDescription(level),
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            _getDateDivisionExample(level),
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              fontFamily: 'monospace',
                              color: Colors.grey[600],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        }),
      ],
    );
  }

  String _getDateDivisionTitle(DateDivisionLevel level) {
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

  String _getDateDivisionDescription(DateDivisionLevel level) {
    switch (level) {
      case DateDivisionLevel.none:
        return 'All photos in one chronological folder';
      case DateDivisionLevel.year:
        return 'Photos organized into yearly folders';
      case DateDivisionLevel.month:
        return 'Photos organized by year and month';
      case DateDivisionLevel.day:
        return 'Photos organized by year, month, and day';
    }
  }

  String _getDateDivisionExample(DateDivisionLevel level) {
    switch (level) {
      case DateDivisionLevel.none:
        return 'ALL_PHOTOS/IMG_1234.jpg';
      case DateDivisionLevel.year:
        return 'ALL_PHOTOS/2023/IMG_1234.jpg';
      case DateDivisionLevel.month:
        return 'ALL_PHOTOS/2023/03_March/IMG_1234.jpg';
      case DateDivisionLevel.day:
        return 'ALL_PHOTOS/2023/03_March/15/IMG_1234.jpg';
    }
  }
}