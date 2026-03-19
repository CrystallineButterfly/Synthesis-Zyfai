
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {YieldMindController} from "src/YieldMindController.sol";

contract YieldMindControllerTest is Test {
    YieldMindController private controller;
    address private admin = address(0xA11CE);
    address private operator = address(0xB0B);
    address private reporter = address(0xCAFE);
    address private target = address(0xD00D);
    bytes4 private selector = bytes4(keccak256("doThing(uint256)"));
    bytes32 private actionId = keccak256("synthesis_zyfai");
    bytes32 private subjectId = keccak256("subject");

    function setUp() public {
        controller = new YieldMindController(admin, operator, reporter, 100 ether);
        vm.startPrank(admin);
        controller.configureActionPolicy(actionId, 20 ether, 40 ether, 1 hours, 0, 0);
        controller.setTargetApproval(target, true);
        controller.setSelectorApproval(selector, true);
        vm.stopPrank();
        vm.prank(reporter);
        controller.reportLiquidBalance(150 ether);
        vm.prank(operator);
        controller.recordDryRun(actionId, keccak256("sim"));
    }

    function testExecuteBoundedActionStoresDigest() public {
        vm.prank(operator);
        bytes32 digest = controller.executeBoundedAction(
            actionId,
            target,
            selector,
            10 ether,
            keccak256("call")
        );
        assertEq(controller.executionDigests(actionId), digest);
        assertEq(controller.trackedLiquidBalance(), 140 ether);
    }

    function testRegisterProfileAndProof() public {
        vm.prank(reporter);
        controller.registerProfile(subjectId, operator, keccak256("manifest"), keccak256("metadata"));
        vm.prank(reporter);
        controller.attachProof(subjectId, keccak256("proof"));
        assertEq(controller.receiptDigests(subjectId), keccak256("proof"));
    }

    function testQueueAndExecuteTask() public {
        vm.prank(reporter);
        controller.queueTask(actionId, target, selector, 5 ether, keccak256("evidence"));
        vm.prank(operator);
        bytes32 digest = controller.executeQueuedTask(actionId, keccak256("task-call"));
        assertEq(controller.executionDigests(actionId), digest);
        assertEq(controller.trackedLiquidBalance(), 145 ether);
    }

    function testExecuteBoundedActionRevertsWithoutReportedBalance() public {
        YieldMindController freshController = new YieldMindController(admin, operator, reporter, 100 ether);
        vm.startPrank(admin);
        freshController.configureActionPolicy(actionId, 20 ether, 40 ether, 1 hours, 0, 0);
        freshController.setTargetApproval(target, true);
        freshController.setSelectorApproval(selector, true);
        vm.stopPrank();

        vm.prank(operator);
        vm.expectRevert(abi.encodeWithSignature("BalanceNotReported()"));
        freshController.executeBoundedAction(
            actionId,
            target,
            selector,
            10 ether,
            keccak256("call")
        );
    }

    function testExecuteBoundedActionRevertsWithoutDryRun() public {
        YieldMindController freshController = new YieldMindController(admin, operator, reporter, 100 ether);
        vm.startPrank(admin);
        freshController.configureActionPolicy(actionId, 20 ether, 40 ether, 1 hours, 0, 0);
        freshController.setTargetApproval(target, true);
        freshController.setSelectorApproval(selector, true);
        vm.stopPrank();
        vm.prank(reporter);
        freshController.reportLiquidBalance(150 ether);

        vm.prank(operator);
        vm.expectRevert(abi.encodeWithSignature("MissingDryRun(bytes32)", actionId));
        freshController.executeBoundedAction(
            actionId,
            target,
            selector,
            10 ether,
            keccak256("call")
        );
    }

    function testExecuteQueuedTaskRevertsWithoutDryRun() public {
        YieldMindController freshController = new YieldMindController(admin, operator, reporter, 100 ether);
        vm.startPrank(admin);
        freshController.configureActionPolicy(actionId, 20 ether, 40 ether, 1 hours, 0, 0);
        freshController.setTargetApproval(target, true);
        freshController.setSelectorApproval(selector, true);
        vm.stopPrank();
        vm.prank(reporter);
        freshController.reportLiquidBalance(150 ether);
        vm.prank(reporter);
        freshController.queueTask(actionId, target, selector, 5 ether, keccak256("evidence"));

        vm.prank(operator);
        vm.expectRevert(abi.encodeWithSignature("MissingDryRun(bytes32)", actionId));
        freshController.executeQueuedTask(actionId, keccak256("task-call"));
    }

}
