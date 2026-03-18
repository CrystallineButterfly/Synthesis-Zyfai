// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

contract YieldMindController is AccessControl, Pausable, ReentrancyGuard {
    bytes32 public constant OPERATOR_ROLE = keccak256("OPERATOR_ROLE");

    struct SpendPolicy {
        bool enabled;
        uint256 cap;
        uint48 cooldown;
        uint48 lastExecution;
    }

    mapping(bytes32 actionId => SpendPolicy policy) private spendPolicies;
    mapping(address target => bool allowed) public approvedTargets;
    mapping(bytes32 actionId => bytes32 simulationHash) public lastDryRun;

    error TargetNotApproved(address target);
    error PolicyMissing(bytes32 actionId);
    error SpendCapExceeded(bytes32 actionId, uint256 amount, uint256 cap);
    error CooldownActive(bytes32 actionId, uint256 nextExecution);

    event SpendPolicyConfigured(bytes32 indexed actionId, uint256 cap, uint48 cooldown);
    event TargetApprovalUpdated(address indexed target, bool allowed);
    event DryRunRecorded(bytes32 indexed actionId, bytes32 indexed simulationHash);
    event ActionExecuted(
        bytes32 indexed actionId,
        address indexed target,
        uint256 amount,
        bytes32 callHash
    );

    constructor(address admin, address operator) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(OPERATOR_ROLE, operator);
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }

    function configureSpendPolicy(
        bytes32 actionId,
        uint256 cap,
        uint48 cooldown
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        spendPolicies[actionId] = SpendPolicy({
            enabled: true,
            cap: cap,
            cooldown: cooldown,
            lastExecution: spendPolicies[actionId].lastExecution
        });
        emit SpendPolicyConfigured(actionId, cap, cooldown);
    }

    function setTarget(address target, bool allowed) external onlyRole(DEFAULT_ADMIN_ROLE) {
        approvedTargets[target] = allowed;
        emit TargetApprovalUpdated(target, allowed);
    }

    function recordDryRun(
        bytes32 actionId,
        bytes32 simulationHash
    ) external onlyRole(OPERATOR_ROLE) whenNotPaused {
        lastDryRun[actionId] = simulationHash;
        emit DryRunRecorded(actionId, simulationHash);
    }

    function executeAction(
        bytes32 actionId,
        address target,
        uint256 amount,
        bytes32 callHash
    ) external onlyRole(OPERATOR_ROLE) whenNotPaused nonReentrant {
        if (!approvedTargets[target]) {
            revert TargetNotApproved(target);
        }

        SpendPolicy storage policy = spendPolicies[actionId];
        if (!policy.enabled) {
            revert PolicyMissing(actionId);
        }
        if (amount > policy.cap) {
            revert SpendCapExceeded(actionId, amount, policy.cap);
        }

        uint256 nextExecution = uint256(policy.lastExecution) + uint256(policy.cooldown);
        if (policy.lastExecution != 0 && block.timestamp < nextExecution) {
            revert CooldownActive(actionId, nextExecution);
        }

        policy.lastExecution = uint48(block.timestamp);
        emit ActionExecuted(actionId, target, amount, callHash);
    }

    function spendPolicy(bytes32 actionId) external view returns (SpendPolicy memory) {
        return spendPolicies[actionId];
    }
}
