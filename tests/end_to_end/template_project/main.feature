Feature: Starting the application
  As a developer using the template
  I want the application to start with the configuration of the selected environment
  So that I can change its behaviour without editing any code

  Background:
    Given a working directory containing a copy of the template configuration

  Scenario: Start in the default environment
    Given no environment is selected
    When I start the application
    Then the application exits successfully
    And the log announces that "template-project" started in the "local" environment
    And debug messages are shown in the log

  Scenario Outline: The log level follows the selected environment
    Given the "<environment>" environment is selected
    When I start the application
    Then the application exits successfully
    And messages below the "<level>" level are hidden from the log

    Examples:
      | environment | level   |
      | local       | DEBUG   |
      | docker      | INFO    |
      | docker_prod | WARNING |

  Scenario: The production environment writes structured logs
    Given the "docker_prod" environment is selected
    And the log level is forced to "INFO"
    When I start the application
    Then the application exits successfully
    And every log line is valid JSON

  Scenario: The log level can be forced without editing the configuration
    Given the "docker_prod" environment is selected
    And the log level is forced to "DEBUG"
    When I start the application
    Then the application exits successfully
    And debug messages are shown in the log

  Scenario: Start with an unknown environment
    Given the "staging" environment is selected
    When I start the application
    Then the application exits with an error
    And the error message names the unknown environment "staging"
    And the error message lists the available environments

  Scenario: Start with an invalid forced log level
    Given no environment is selected
    And the log level is forced to "VERBOSE"
    When I start the application
    Then the application exits with an error
    And the error message names the invalid log level "VERBOSE"

  Scenario: Start without configuration files
    Given the configuration directory is missing
    When I start the application
    Then the application exits with an error
    And the error message says that a configuration file was not found

  Scenario: Start with an empty application name
    Given the configured application name is empty
    When I start the application
    Then the application exits with an error
    And the error message says that the application name must not be empty
