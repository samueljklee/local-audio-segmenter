#!/usr/bin/env python3
"""
Configuration Profile Management Demo

This script demonstrates how to use the configuration system
to create, customize, and manage profiles for different audio content types.
"""

import sys
import json
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from config.settings import ConfigManager
    from config.profile_loader import ProfileLoader
    from config.validator import ConfigValidationError
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure all dependencies are installed:")
    print("  pip install PyYAML jsonschema")
    sys.exit(1)


def demo_profile_listing():
    """Demonstrate listing available profiles."""
    print("🔍 Profile Listing Demo")
    print("=" * 50)

    try:
        loader = ProfileLoader("src/config/profiles")
        profiles = loader.list_profiles()

        print(f"Found {len(profiles)} available profiles:")
        for profile in profiles:
            print(f"  • {profile}")

        return profiles
    except Exception as e:
        print(f"Error listing profiles: {e}")
        return []


def demo_profile_info(profile_name):
    """Demonstrate getting detailed profile information."""
    print(f"\n📋 Profile Information Demo: {profile_name}")
    print("=" * 50)

    try:
        loader = ProfileLoader("src/config/profiles")
        info = loader.get_profile_info(profile_name)

        print(f"Profile: {info['name']}")
        print(f"Type: {info['profile']}")
        print(f"Domain: {info.get('domain', {}).get('type', 'unknown')}")

        if info.get('domain', {}).get('language'):
            print(f"Language: {info['domain']['language']}")

        characteristics = info.get('domain', {}).get('characteristics', [])
        if characteristics:
            print(f"Characteristics: {', '.join(characteristics)}")

        print(f"\nSemantic Labeling: {info['semantic_labeling']['enabled']}")
        if info['semantic_labeling']['enabled']:
            print(f"  • Categories: {info['semantic_labeling']['categories_count']}")
            print(f"  • Rules: {info['semantic_labeling']['rules_count']}")

        print(f"\nAudio Settings:")
        audio = info.get('audio', {})
        print(f"  • Sample Rate: {audio.get('sample_rate', 'default')} Hz")
        print(f"  • Channels: {audio.get('channels', 'default')}")
        print(f"  • Format: {audio.get('format', 'default')}")

        print(f"\nSegmentation:")
        seg = info.get('segmentation', {})
        print(f"  • Method: {seg.get('method', 'default')}")
        print(f"  • Min Length: {seg.get('min_segment_length', 'default')}s")
        print(f"  • Max Length: {seg.get('max_segment_length', 'default')}s")

    except Exception as e:
        print(f"Error getting profile info: {e}")


def demo_profile_loading(profile_name):
    """Demonstrate loading and using a profile."""
    print(f"\n⚙️ Profile Loading Demo: {profile_name}")
    print("=" * 50)

    try:
        config_manager = ConfigManager(profile=profile_name)

        print(f"✓ Successfully loaded profile: {profile_name}")
        print(f"✓ Profile identifier: {config_manager.get('profile', 'none')}")
        print(f"✓ Semantic labeling enabled: {config_manager.is_semantic_labeling_enabled}")

        if config_manager.is_semantic_labeling_enabled:
            print(f"✓ Semantic categories: {len(config_manager.semantic_categories)}")
            print(f"✓ Semantic rules: {len(config_manager.semantic_rules)}")

            # Show a few categories
            print("\nSemantic Categories:")
            for i, (name, category) in enumerate(config_manager.semantic_categories.items()):
                if i >= 3:  # Show first 3 categories
                    break
                description = category.get('description', 'No description')
                color = category.get('color', 'No color')
                print(f"  • {name}: {description} ({color})")

            # Show a few rules
            print("\nSemantic Rules:")
            for i, rule in enumerate(config_manager.semantic_rules):
                if i >= 3:  # Show first 3 rules
                    break
                name = rule.get('name', 'unnamed')
                label = rule.get('label', 'no label')
                priority = rule.get('priority', 'unknown')
                print(f"  • {name} → {label} (priority: {priority})")

    except Exception as e:
        print(f"❌ Error loading profile: {e}")


def demo_custom_profile_creation():
    """Demonstrate creating a custom profile."""
    print(f"\n🎨 Custom Profile Creation Demo")
    print("=" * 50)

    try:
        loader = ProfileLoader("src/config/profiles")

        # Define custom overrides
        overrides = {
            "profile": "demo_custom_podcast",
            "audio": {
                "sample_rate": 48000,
                "bit_depth": 24,
                "channels": 2
            },
            "semantic_labeling": {
                "categories": {
                    "sponsor_segment": {
                        "description": "Sponsored content segment",
                        "color": "#FF5722",
                        "min_duration": 15
                    }
                },
                "rules": [
                    {
                        "name": "detect_sponsor",
                        "label": "sponsor_segment",
                        "priority": 6,
                        "confidence_threshold": 0.7,
                        "pattern": {
                            "min_duration": 15,
                            "max_duration": 120,
                            "energy_range": {"min": 0.15, "max": 0.8}
                        }
                    }
                ]
            },
            "output": {
                "format": "flac",
                "quality": "high",
                "visualization": {"enabled": true}
            }
        }

        print("Creating custom profile based on 'podcast'...")
        custom_profile = loader.create_custom_profile("demo_custom_podcast", "podcast", overrides)

        print(f"✓ Custom profile created successfully!")
        print(f"✓ Sample rate: {custom_profile['audio']['sample_rate']} Hz")
        print(f"✓ Bit depth: {custom_profile['audio']['bit_depth']} bits")
        print(f"✓ Channels: {custom_profile['audio']['channels']}")
        print(f"✓ New categories: {len(custom_profile['semantic_labeling']['categories'])}")
        print(f"✓ New rules: {len(custom_profile['semantic_labeling']['rules'])}")

        # Show the custom category
        sponsor_cat = custom_profile['semantic_labeling']['categories']['sponsor_segment']
        print(f"✓ Custom category: {sponsor_cat['description']} ({sponsor_cat['color']})")

        return custom_profile

    except Exception as e:
        print(f"❌ Error creating custom profile: {e}")
        return None


def demo_configuration_modification():
    """Demonstrate modifying configuration values."""
    print(f"\n✏️ Configuration Modification Demo")
    print("=" * 50)

    try:
        config_manager = ConfigManager(profile="lecture")

        print(f"Original silence threshold: {config_manager.get('segmentation.silence_threshold')} dB")

        # Modify configuration
        config_manager.set("segmentation.silence_threshold", -35)
        config_manager.set("segmentation.min_segment_length", 10.0)
        config_manager.set("audio.sample_rate", 48000)

        print(f"✓ Modified silence threshold: {config_manager.get('segmentation.silence_threshold')} dB")
        print(f"✓ Modified min segment length: {config_manager.get('segmentation.min_segment_length')}s")
        print(f"✓ Modified sample rate: {config_manager.get('audio.sample_rate')} Hz")

        # Test invalid configuration
        try:
            config_manager.set("audio.sample_rate", -1000)  # Invalid
            print("❌ Should have failed validation!")
        except ConfigValidationError:
            print("✓ Configuration validation caught invalid value")

    except Exception as e:
        print(f"❌ Error modifying configuration: {e}")


def demo_semantic_access():
    """Demonstrate semantic labeling API access."""
    print(f"\n🏷️ Semantic Labeling API Demo")
    print("=" * 50)

    try:
        config_manager = ConfigManager(profile="church_service")

        if not config_manager.is_semantic_labeling_enabled:
            print("Semantic labeling is not enabled for this profile")
            return

        print(f"Semantic labeling enabled: {config_manager.is_semantic_labeling_enabled}")

        # Access categories
        print(f"\nTotal categories: {len(config_manager.semantic_categories)}")
        print("Category examples:")
        for i, (name, category) in enumerate(config_manager.semantic_categories.items()):
            if i >= 2:  # Show first 2
                break
            description = category.get('description', 'No description')
            min_duration = category.get('min_duration', 'Not specified')
            print(f"  • {name}: {description} (min: {min_duration}s)")

        # Access rules for specific labels
        sermon_rules = config_manager.get_semantic_rules_for_label("sermon")
        print(f"\nRules for 'sermon' label: {len(sermon_rules)}")
        for rule in sermon_rules:
            name = rule.get('name', 'unnamed')
            confidence = rule.get('confidence_threshold', 'unknown')
            print(f"  • {name} (confidence: {confidence})")

        # Access specific category
        sermon_category = config_manager.get_semantic_category("sermon")
        if sermon_category:
            print(f"\nSermon category details:")
            print(f"  • Description: {sermon_category.get('description', 'N/A')}")
            print(f"  • Color: {sermon_category.get('color', 'N/A')}")
            print(f"  • Icon: {sermon_category.get('icon', 'N/A')}")

    except Exception as e:
        print(f"❌ Error accessing semantic labeling: {e}")


def demo_configuration_export():
    """Demonstrate exporting and saving configurations."""
    print(f"\n💾 Configuration Export Demo")
    print("=" * 50)

    try:
        config_manager = ConfigManager(profile="meeting")

        # Modify some settings
        config_manager.set("audio.sample_rate", 48000)
        config_manager.set("output.format", "flac")
        config_manager.set("performance.use_gpu", True)

        # Export to dictionary
        config_dict = config_manager.to_dict()

        print(f"✓ Configuration exported to dictionary")
        print(f"✓ Profile: {config_dict.get('profile', 'unknown')}")
        print(f"✓ Total sections: {len(config_dict)}")

        # Show key sections
        key_sections = ['audio', 'segmentation', 'output', 'semantic_labeling']
        for section in key_sections:
            if section in config_dict:
                print(f"✓ {section}: {len(config_dict[section])} properties")

        # Save to file (demo)
        output_file = Path("examples/configurations/demo_exported_config.yaml")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            config_manager.save_config(output_file)
            print(f"✓ Configuration saved to: {output_file}")
        except Exception as save_error:
            print(f"⚠️ Could not save file (this is expected in demo): {save_error}")

    except Exception as e:
        print(f"❌ Error exporting configuration: {e}")


def main():
    """Run all demonstration functions."""
    print("🚀 Audio Auto-Segmentation Configuration System Demo")
    print("=" * 60)

    # Demo 1: Profile listing
    profiles = demo_profile_listing()
    if not profiles:
        print("❌ No profiles found, cannot continue with demo")
        return

    # Demo 2: Profile information (use first available profile)
    demo_profile_info(profiles[0])

    # Demo 3: Profile loading
    demo_profile_loading(profiles[0])

    # Demo 4: Custom profile creation
    custom_profile = demo_custom_profile_creation()

    # Demo 5: Configuration modification
    demo_configuration_modification()

    # Demo 6: Semantic labeling API
    demo_semantic_access()

    # Demo 7: Configuration export
    demo_configuration_export()

    print(f"\n✅ Demo completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Try the CLI tools: config-cli --help")
    print("2. Load profiles in your own code")
    print("3. Create custom profiles for your specific needs")
    print("4. Experiment with semantic labeling rules")


if __name__ == "__main__":
    main()