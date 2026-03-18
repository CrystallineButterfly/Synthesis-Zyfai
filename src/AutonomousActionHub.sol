// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AutonomousActionCore} from "src/AutonomousActionCore.sol";

contract AutonomousActionHub is AutonomousActionCore {
    struct Profile {
        address operator;
        bytes32 manifestHash;
        bytes32 metadataHash;
        uint96 reputation;
        bool active;
        uint64 updatedAt;
    }

    struct QueuedTask {
        address target;
        bytes4 selector;
        uint128 amount;
        bytes32 evidenceHash;
        uint64 queuedAt;
        bool executed;
    }

    uint256 public principalFloor;
    uint256 public trackedLiquidBalance;
    uint64 public lastBalanceReportAt;
    mapping(bytes32 => Profile) public profiles;
    mapping(bytes32 => QueuedTask) public queuedTasks;

    error PrincipalFloorBreached(uint256 liquidBalance, uint256 principalFloor, uint256 requestedAmount);
    error ProfileMissing(bytes32 subjectId);
    error UnknownTask(bytes32 actionId);
    error TaskAlreadyExecuted(bytes32 actionId);
    error BalanceNotReported();

    event LiquidBalanceReported(uint256 liquidBalance, uint64 reportedAt);

    constructor(
        address admin,
        address operator,
        address reporter,
        uint256 initialPrincipalFloor
    ) AutonomousActionCore(admin, operator, reporter) {
        principalFloor = initialPrincipalFloor;
    }

    function setPrincipalFloor(uint256 newPrincipalFloor)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        principalFloor = newPrincipalFloor;
    }

    function reportLiquidBalance(uint256 liquidBalance)
        external
        onlyRole(REPORTER_ROLE)
        whenNotPaused
    {
        trackedLiquidBalance = liquidBalance;
        lastBalanceReportAt = uint64(block.timestamp);
        emit LiquidBalanceReported(liquidBalance, lastBalanceReportAt);
    }

    function spendableBuffer() public view returns (uint256) {
        return trackedLiquidBalance > principalFloor ? trackedLiquidBalance - principalFloor : 0;
    }

    function executeBoundedAction(
        bytes32 actionId,
        address target,
        bytes4 selector,
        uint256 amount,
        bytes32 callHash
    ) external onlyRole(OPERATOR_ROLE) whenNotPaused nonReentrant returns (bytes32) {
        uint256 liquidBalance = trackedLiquidBalance;
        if (lastBalanceReportAt == 0) {
            revert BalanceNotReported();
        }
        if (amount > spendableBuffer()) {
            revert PrincipalFloorBreached(liquidBalance, principalFloor, amount);
        }
        _consumePolicy(actionId, amount);
        _enforceTargetAndSelector(target, selector);
        bytes32 digest = keccak256(
            abi.encode(actionId, target, selector, amount, liquidBalance, callHash)
        );
        executionDigests[actionId] = digest;
        trackedLiquidBalance = liquidBalance - amount;
        return digest;
    }

    function registerProfile(
        bytes32 subjectId,
        address operatorAddress,
        bytes32 manifestHash,
        bytes32 metadataHash
    ) external onlyRole(REPORTER_ROLE) whenNotPaused {
        profiles[subjectId] = Profile({
            operator: operatorAddress,
            manifestHash: manifestHash,
            metadataHash: metadataHash,
            reputation: 0,
            active: true,
            updatedAt: uint64(block.timestamp)
        });
    }

    function updateReputation(
        bytes32 subjectId,
        uint96 newReputation,
        bytes32 evidenceHash
    ) external onlyRole(REPORTER_ROLE) whenNotPaused {
        Profile storage profile = profiles[subjectId];
        if (profile.updatedAt == 0) {
            revert ProfileMissing(subjectId);
        }
        profile.reputation = newReputation;
        profile.updatedAt = uint64(block.timestamp);
        executionDigests[subjectId] = evidenceHash;
    }

    function attachProof(bytes32 subjectId, bytes32 proofDigest)
        external
        onlyRole(REPORTER_ROLE)
        whenNotPaused
    {
        Profile storage profile = profiles[subjectId];
        if (profile.updatedAt == 0) {
            revert ProfileMissing(subjectId);
        }
        receiptDigests[subjectId] = proofDigest;
        profile.updatedAt = uint64(block.timestamp);
    }

    function queueTask(
        bytes32 actionId,
        address target,
        bytes4 selector,
        uint128 amount,
        bytes32 evidenceHash
    ) external onlyRole(REPORTER_ROLE) whenNotPaused {
        queuedTasks[actionId] = QueuedTask({
            target: target,
            selector: selector,
            amount: amount,
            evidenceHash: evidenceHash,
            queuedAt: uint64(block.timestamp),
            executed: false
        });
    }

    function executeQueuedTask(bytes32 actionId, bytes32 callHash)
        external
        onlyRole(OPERATOR_ROLE)
        whenNotPaused
        nonReentrant
        returns (bytes32)
    {
        QueuedTask storage task = queuedTasks[actionId];
        if (task.queuedAt == 0) {
            revert UnknownTask(actionId);
        }
        if (task.executed) {
            revert TaskAlreadyExecuted(actionId);
        }
        uint256 liquidBalance = trackedLiquidBalance;
        if (lastBalanceReportAt == 0) {
            revert BalanceNotReported();
        }
        if (task.amount > spendableBuffer()) {
            revert PrincipalFloorBreached(liquidBalance, principalFloor, task.amount);
        }
        _consumePolicy(actionId, task.amount);
        _enforceTargetAndSelector(task.target, task.selector);
        task.executed = true;
        bytes32 digest = keccak256(
            abi.encode(actionId, task.target, task.selector, task.amount, liquidBalance, callHash)
        );
        executionDigests[actionId] = digest;
        trackedLiquidBalance = liquidBalance - task.amount;
        return digest;
    }
}
