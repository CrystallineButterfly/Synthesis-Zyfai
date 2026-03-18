// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

contract AutonomousActionCore is AccessControl, Pausable, ReentrancyGuard {
    bytes32 public constant OPERATOR_ROLE = keccak256("OPERATOR_ROLE");
    bytes32 public constant REPORTER_ROLE = keccak256("REPORTER_ROLE");

    struct ActionPolicy {
        bool enabled;
        uint128 perActionCap;
        uint128 dailyCap;
        uint64 cooldown;
        uint64 validAfter;
        uint64 validBefore;
        uint64 lastExecutedAt;
        uint128 spentToday;
        uint32 lastSpentDay;
    }

    mapping(bytes32 => ActionPolicy) internal actionPolicies;
    mapping(address => bool) public approvedTargets;
    mapping(bytes4 => bool) public approvedSelectors;
    mapping(bytes32 => bytes32) public lastDryRun;
    mapping(bytes32 => bytes32) public executionDigests;
    mapping(bytes32 => bytes32) public receiptDigests;

    error PolicyMissing(bytes32 actionId);
    error TargetNotApproved(address target);
    error SelectorNotApproved(bytes4 selector);
    error PerActionCapExceeded(bytes32 actionId, uint256 amount, uint256 cap);
    error DailyLimitExceeded(bytes32 actionId, uint256 amount, uint256 cap);
    error CooldownActive(bytes32 actionId, uint256 nextAllowedTimestamp);
    error OutsideWindow(bytes32 actionId, uint256 timestamp);

    event ActionPolicyConfigured(bytes32 indexed actionId, uint128 perActionCap, uint128 dailyCap, uint64 cooldown, uint64 validAfter, uint64 validBefore);
    event TargetApprovalUpdated(address indexed target, bool allowed);
    event SelectorApprovalUpdated(bytes4 indexed selector, bool allowed);
    event DryRunRecorded(bytes32 indexed actionId, bytes32 indexed simulationHash);
    event ExecutionDigestRecorded(bytes32 indexed actionId, bytes32 indexed executionDigest);
    event ReceiptRecorded(bytes32 indexed subjectId, bytes32 indexed receiptDigest);

    constructor(address admin, address operator, address reporter) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(OPERATOR_ROLE, operator);
        _grantRole(REPORTER_ROLE, reporter);
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) { _unpause(); }

    function setTargetApproval(address target, bool allowed) external onlyRole(DEFAULT_ADMIN_ROLE) {
        approvedTargets[target] = allowed;
        emit TargetApprovalUpdated(target, allowed);
    }

    function setSelectorApproval(bytes4 selector, bool allowed) external onlyRole(DEFAULT_ADMIN_ROLE) {
        approvedSelectors[selector] = allowed;
        emit SelectorApprovalUpdated(selector, allowed);
    }

    function configureActionPolicy(bytes32 actionId, uint128 perActionCap, uint128 dailyCap, uint64 cooldown, uint64 validAfter, uint64 validBefore) external onlyRole(DEFAULT_ADMIN_ROLE) {
        ActionPolicy storage existing = actionPolicies[actionId];
        actionPolicies[actionId] = ActionPolicy({
            enabled: true,
            perActionCap: perActionCap,
            dailyCap: dailyCap,
            cooldown: cooldown,
            validAfter: validAfter,
            validBefore: validBefore,
            lastExecutedAt: existing.lastExecutedAt,
            spentToday: existing.spentToday,
            lastSpentDay: existing.lastSpentDay
        });
        emit ActionPolicyConfigured(actionId, perActionCap, dailyCap, cooldown, validAfter, validBefore);
    }

    function recordDryRun(bytes32 actionId, bytes32 simulationHash) external onlyRole(OPERATOR_ROLE) whenNotPaused {
        lastDryRun[actionId] = simulationHash;
        emit DryRunRecorded(actionId, simulationHash);
    }

    function recordExecutionDigest(bytes32 actionId, bytes32 executionDigest) public onlyRole(REPORTER_ROLE) whenNotPaused {
        executionDigests[actionId] = executionDigest;
        emit ExecutionDigestRecorded(actionId, executionDigest);
    }

    function recordReceipt(bytes32 subjectId, bytes32 receiptDigest) external onlyRole(REPORTER_ROLE) whenNotPaused {
        receiptDigests[subjectId] = receiptDigest;
        emit ReceiptRecorded(subjectId, receiptDigest);
    }

    function _consumePolicy(bytes32 actionId, uint256 amount) internal {
        ActionPolicy storage policy = actionPolicies[actionId];
        if (!policy.enabled) revert PolicyMissing(actionId);
        if (policy.validAfter != 0 && block.timestamp < policy.validAfter) revert OutsideWindow(actionId, block.timestamp);
        if (policy.validBefore != 0 && block.timestamp > policy.validBefore) revert OutsideWindow(actionId, block.timestamp);
        if (amount > policy.perActionCap) revert PerActionCapExceeded(actionId, amount, policy.perActionCap);
        uint256 nextExecution = uint256(policy.lastExecutedAt) + uint256(policy.cooldown);
        if (policy.lastExecutedAt != 0 && block.timestamp < nextExecution) revert CooldownActive(actionId, nextExecution);
        uint32 dayKey = uint32(block.timestamp / 1 days);
        if (policy.lastSpentDay != dayKey) {
            policy.lastSpentDay = dayKey;
            policy.spentToday = 0;
        }
        uint256 nextSpent = uint256(policy.spentToday) + amount;
        if (nextSpent > policy.dailyCap) revert DailyLimitExceeded(actionId, nextSpent, policy.dailyCap);
        policy.spentToday = uint128(nextSpent);
        policy.lastExecutedAt = uint64(block.timestamp);
    }

    function _enforceTargetAndSelector(address target, bytes4 selector) internal view {
        if (!approvedTargets[target]) revert TargetNotApproved(target);
        if (!approvedSelectors[selector]) revert SelectorNotApproved(selector);
    }
}
