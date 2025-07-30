"""
Service Container for Dependency Injection

This module provides a comprehensive dependency injection system for the Google Photos
Takeout Helper application. It manages service lifecycles, handles dependencies,
and provides a clean separation of concerns.

Features:
- Singleton and transient service registration
- Automatic dependency resolution
- Service lifecycle management
- Configuration injection
- Factory pattern support
- Circular dependency detection

Based on Dart reference: dart-version/lib/shared/service_container.dart
"""

import inspect
import logging
from typing import Any, Type, TypeVar, Dict, Callable, Optional, Set, List
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceLifetime(Enum):
    """Service lifetime management modes."""
    SINGLETON = "singleton"  # One instance for the container lifetime
    TRANSIENT = "transient"  # New instance every time
    SCOPED = "scoped"  # One instance per scope (future use)


@dataclass
class ServiceDescriptor:
    """Describes how a service should be created and managed."""
    service_type: Type
    implementation_type: Optional[Type] = None
    factory: Optional[Callable] = None
    lifetime: ServiceLifetime = ServiceLifetime.SINGLETON
    instance: Optional[Any] = None
    dependencies: List[Type] = field(default_factory=list)
    is_initialized: bool = False


class ServiceContainer:
    """
    Dependency injection container that manages service creation,
    lifetime, and dependency resolution.
    """
    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._instances: Dict[Type, Any] = {}
        self._resolution_stack: Set[Type] = set()
        self._configuration: Dict[str, Any] = {}
        self._logger = logging.getLogger(__name__)
    def register_singleton(self, service_type: Type[T], 
                          implementation_type: Optional[Type[T]] = None) -> 'ServiceContainer':
        """
        Register a service as a singleton.
        
        Args:
            service_type: The service interface/type to register
            implementation_type: The concrete implementation (defaults to service_type)
        Returns:
            Self for method chaining
        """
        impl_type = implementation_type or service_type
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=impl_type,
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=self._extract_dependencies(impl_type)
        )
        self._services[service_type] = descriptor
        self._logger.debug(f"Registered singleton: {service_type.__name__} -> {impl_type.__name__}")
        return self
    def register_transient(self, service_type: Type[T], 
                          implementation_type: Optional[Type[T]] = None) -> 'ServiceContainer':
        """
        Register a service as transient (new instance every time).
        
        Args:
            service_type: The service interface/type to register
            implementation_type: The concrete implementation (defaults to service_type)
        Returns:
            Self for method chaining
        """
        impl_type = implementation_type or service_type
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=impl_type,
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=self._extract_dependencies(impl_type)
        )
        self._services[service_type] = descriptor
        self._logger.debug(f"Registered transient: {service_type.__name__} -> {impl_type.__name__}")
        return self
    def register_factory(self, service_type: Type[T], 
                        factory: Callable[..., T],
                        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON) -> 'ServiceContainer':
        """
        Register a service using a factory function.
        
        Args:
            service_type: The service type to register
            factory: Factory function that creates the service
            lifetime: Service lifetime
        Returns:
            Self for method chaining
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            factory=factory,
            lifetime=lifetime,
            dependencies=self._extract_factory_dependencies(factory)
        )
        self._services[service_type] = descriptor
        self._logger.debug(f"Registered factory: {service_type.__name__}")
        return self
    def register_instance(self, service_type: Type[T], instance: T) -> 'ServiceContainer':
        """
        Register a pre-created instance as a singleton.
        
        Args:
            service_type: The service type
            instance: The pre-created instance
        Returns:
            Self for method chaining
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            lifetime=ServiceLifetime.SINGLETON,
            instance=instance,
            is_initialized=True
        )
        self._services[service_type] = descriptor
        self._instances[service_type] = instance
        self._logger.debug(f"Registered instance: {service_type.__name__}")
        return self
    def get_service(self, service_type: Type[T]) -> T:
        """
        Resolve and return a service instance.
        
        Args:
            service_type: The type of service to resolve
        Returns:
            Instance of the requested service
        Raises:
            ServiceNotRegistered: If service is not registered
            CircularDependencyError: If circular dependency detected
        """
        try:
            return self._resolve_service(service_type)
        except Exception as e:
            self._logger.error(f"Failed to resolve service {service_type.__name__}: {e}")
            raise
    def get_required_service(self, service_type: Type[T]) -> T:
        """
        Get a service that must exist (raises if not found).
        
        Args:
            service_type: The service type to get
        Returns:
            The service instance
        Raises:
            ServiceNotRegistered: If service is not registered
        """
        if service_type not in self._services:
            raise ServiceNotRegistered(f"Service {service_type.__name__} is not registered")
        return self.get_service(service_type)
    def try_get_service(self, service_type: Type[T]) -> Optional[T]:
        """
        Try to get a service, returning None if not found.
        
        Args:
            service_type: The service type to get
        Returns:
            The service instance or None
        """
        try:
            return self.get_service(service_type)
        except ServiceNotRegistered:
            return None
        except Exception as e:
            self._logger.warning(f"Error resolving optional service {service_type.__name__}: {e}")
            return None
    def set_configuration(self, config: Dict[str, Any]) -> 'ServiceContainer':
        """
        Set configuration values that can be injected into services.
        
        Args:
            config: Configuration dictionary
        Returns:
            Self for method chaining
        """
        self._configuration.update(config)
        return self
    def get_configuration(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._configuration.get(key, default)
    def is_registered(self, service_type: Type) -> bool:
        """Check if a service type is registered."""
        return service_type in self._services
    def get_services_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all registered services."""
        info = {}
        for service_type, descriptor in self._services.items():
            info[service_type.__name__] = {
                'implementation': descriptor.implementation_type.__name__ if descriptor.implementation_type else 'Factory',
                'lifetime': descriptor.lifetime.value,
                'dependencies': [dep.__name__ for dep in descriptor.dependencies],
                'initialized': descriptor.is_initialized
            }
        return info
    def _resolve_service(self, service_type: Type[T]) -> T:
        """
        Internal service resolution with circular dependency detection.
        
        Args:
            service_type: The service type to resolve
        Returns:
            The resolved service instance
        """
        # Check for circular dependencies
        if service_type in self._resolution_stack:
            dependency_chain = " -> ".join(t.__name__ for t in self._resolution_stack)
            raise CircularDependencyError(
                f"Circular dependency detected: {dependency_chain} -> {service_type.__name__}"
            )
        # Check if service is registered
        if service_type not in self._services:
            raise ServiceNotRegistered(f"Service {service_type.__name__} is not registered")
        descriptor = self._services[service_type]
        # Return existing singleton instance
        if descriptor.lifetime == ServiceLifetime.SINGLETON and service_type in self._instances:
            return self._instances[service_type]
        # If already have instance, return it
        if descriptor.instance is not None:
            return descriptor.instance
        # Add to resolution stack for circular dependency detection
        self._resolution_stack.add(service_type)
        try:
            # Create new instance
            if descriptor.factory:
                instance = self._create_from_factory(descriptor)
            else:
                instance = self._create_from_type(descriptor)
            # Store singleton instances
            if descriptor.lifetime == ServiceLifetime.SINGLETON:
                self._instances[service_type] = instance
                descriptor.instance = instance
                descriptor.is_initialized = True
            return instance
        finally:
            # Remove from resolution stack
            self._resolution_stack.discard(service_type)
    def _create_from_factory(self, descriptor: ServiceDescriptor) -> Any:
        """Create service instance using factory function."""
        if not descriptor.factory:
            raise ValueError("Factory function is required")
        # Resolve factory dependencies
        resolved_deps = {}
        factory_sig = inspect.signature(descriptor.factory)
        for param_name, param in factory_sig.parameters.items():
            if param.annotation and param.annotation != inspect.Parameter.empty:
                # Special handling for configuration
                if param_name.startswith('config_'):
                    config_key = param_name[7:]  # Remove 'config_' prefix
                    resolved_deps[param_name] = self.get_configuration(config_key)
                else:
                    resolved_deps[param_name] = self._resolve_service(param.annotation)
        return descriptor.factory(**resolved_deps)
    def _create_from_type(self, descriptor: ServiceDescriptor) -> Any:
        """Create service instance from type with dependency injection."""
        if not descriptor.implementation_type:
            raise ValueError("Implementation type is required")
        # Resolve constructor dependencies
        resolved_deps = []
        for dep_type in descriptor.dependencies:
            resolved_deps.append(self._resolve_service(dep_type))
        # Create instance
        try:
            return descriptor.implementation_type(*resolved_deps)
        except Exception as e:
            raise ServiceCreationError(
                f"Failed to create {descriptor.implementation_type.__name__}: {e}"
            )
    def _extract_dependencies(self, implementation_type: Type) -> List[Type]:
        """Extract constructor dependencies from a type."""
        try:
            signature = inspect.signature(implementation_type.__init__)
            dependencies = []
            for param_name, param in signature.parameters.items():
                if param_name == 'self':
                    continue
                if param.annotation and param.annotation != inspect.Parameter.empty:
                    if not param_name.startswith('config_'):  # Skip config parameters
                        dependencies.append(param.annotation)
            return dependencies
        except Exception as e:
            self._logger.warning(f"Could not extract dependencies for {implementation_type.__name__}: {e}")
            return []
    def _extract_factory_dependencies(self, factory: Callable) -> List[Type]:
        """Extract dependencies from a factory function."""
        try:
            signature = inspect.signature(factory)
            dependencies = []
            for param_name, param in signature.parameters.items():
                if param.annotation and param.annotation != inspect.Parameter.empty:
                    if not param_name.startswith('config_'):  # Skip config parameters
                        dependencies.append(param.annotation)
            return dependencies
        except Exception as e:
            self._logger.warning(f"Could not extract factory dependencies: {e}")
            return []
    def dispose(self) -> None:
        """Dispose all singleton instances that implement IDisposable."""
        for instance in self._instances.values():
            if hasattr(instance, 'dispose'):
                try:
                    instance.dispose()
                except Exception as e:
                    self._logger.warning(f"Error disposing {type(instance).__name__}: {e}")
        self._instances.clear()
        self._services.clear()
        self._configuration.clear()


# Exception classes
class ServiceContainerError(Exception):
    """Base exception for service container errors."""
    pass


class ServiceNotRegistered(ServiceContainerError):
    """Raised when trying to resolve an unregistered service."""
    pass


class CircularDependencyError(ServiceContainerError):
    """Raised when circular dependency is detected.""" 
    pass


class ServiceCreationError(ServiceContainerError):
    """Raised when service creation fails."""
    pass


# Service interfaces for common patterns
class IDisposable(ABC):
    """Interface for services that need cleanup."""
    @abstractmethod
    def dispose(self) -> None:
        """Clean up resources."""
        pass


class ServiceContainerBuilder:
    """Builder pattern for configuring a service container."""
    def __init__(self):
        self.container = ServiceContainer()
    def add_singleton(self, service_type: Type[T], 
                     implementation_type: Optional[Type[T]] = None) -> 'ServiceContainerBuilder':
        """Add a singleton service."""
        self.container.register_singleton(service_type, implementation_type)
        return self
    def add_transient(self, service_type: Type[T], 
                     implementation_type: Optional[Type[T]] = None) -> 'ServiceContainerBuilder':
        """Add a transient service."""
        self.container.register_transient(service_type, implementation_type)
        return self
    def add_factory(self, service_type: Type[T], factory: Callable[..., T],
                   lifetime: ServiceLifetime = ServiceLifetime.SINGLETON) -> 'ServiceContainerBuilder':
        """Add a factory-created service."""
        self.container.register_factory(service_type, factory, lifetime)
        return self
    def add_instance(self, service_type: Type[T], instance: T) -> 'ServiceContainerBuilder':
        """Add a pre-created instance."""
        self.container.register_instance(service_type, instance)
        return self
    def add_configuration(self, config: Dict[str, Any]) -> 'ServiceContainerBuilder':
        """Add configuration values."""
        self.container.set_configuration(config)
        return self
    def build(self) -> ServiceContainer:
        """Build the configured container."""
        return self.container


def create_service_container() -> ServiceContainerBuilder:
    """Factory function to create a service container builder."""
    return ServiceContainerBuilder()


# Global container instance for application-wide use
_global_container: Optional[ServiceContainer] = None


def get_global_container() -> ServiceContainer:
    """Get the global service container instance."""
    global _global_container
    if _global_container is None:
        _global_container = ServiceContainer()
    return _global_container


def set_global_container(container: ServiceContainer) -> None:
    """Set the global service container instance."""
    global _global_container
    _global_container = container


def reset_global_container() -> None:
    """Reset the global container (mainly for testing)."""
    global _global_container
    if _global_container:
        _global_container.dispose()
    _global_container = None