// ignore_for_file: unintended_html_in_doc_comment

import '../lib/cli/gpth_cli.dart';

/// ############################### GOOGLE PHOTOS TAKEOUT HELPER #############################
///
/// **REFACTORED MAIN ENTRY POINT**
/// 
/// This is the refactored main entry point for the Google Photos Takeout Helper (GPTH).
/// The application has been restructured to separate concerns:
/// 
/// - **CLI Interface** (`lib/cli/gpth_cli.dart`): Handles command line parsing and user interaction
/// - **Core API** (`lib/core/api/gpth_core_api.dart`): Provides clean business logic interface
/// - **Domain Services** (`lib/domain/`): Contains all processing logic and business rules
/// 
/// This separation enables:
/// - Easy integration of different user interfaces (CLI, GUI, web, etc.)
/// - Better testability and maintainability
/// - Clear separation of concerns
/// - Reusable core functionality
///
/// **USAGE:**
/// ```bash
/// dart run bin/gpth_refactored.dart [options]
/// ```
///
/// **PROCESSING FLOW:**
/// 1. CLI parses command line arguments → ProcessingConfig
/// 2. Core API initializes dependencies (ExifTool, ServiceContainer)
/// 3. Core API executes ProcessingPipeline with 8 steps:
///    - Fix Extensions: Correct mismatched file extensions (optional)
///    - Discover Media: Find and classify all media files
///    - Remove Duplicates: Eliminate duplicate files using content hashing
///    - Extract Dates: Determine accurate timestamps from multiple sources
///    - Write EXIF: Embed metadata into files (when ExifTool available)
///    - Find Albums: Detect and merge album relationships
///    - Move Files: Organize files to output structure using selected album behavior
///    - Update Creation Time: Sync file creation timestamps (Windows only, optional)
/// 4. Core API returns comprehensive results and statistics
/// 5. CLI displays results to user
///
/// **DESIGN BENEFITS:**
/// - **Modularity**: Each component has a single, clear responsibility
/// - **Testability**: All components are independently testable
/// - **Extensibility**: Easy to add new interfaces or modify existing ones
/// - **Maintainability**: Clear separation makes code easier to understand and modify
/// - **Reusability**: Core functionality can be used by different interfaces
///
/// ##############################################################################

Future<void> main(List<String> arguments) async {
  final cli = GpthCli();
  await cli.run(arguments);
}