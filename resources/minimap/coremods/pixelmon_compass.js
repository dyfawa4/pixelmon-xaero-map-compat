// Embedded in the modified Xaero component. Optional targets are never class-loaded here.
function initializeCoreMod() {
    var Opcodes = Java.type('org.objectweb.asm.Opcodes');
    var InsnList = Java.type('org.objectweb.asm.tree.InsnList');
    var VarInsnNode = Java.type('org.objectweb.asm.tree.VarInsnNode');
    var MethodInsnNode = Java.type('org.objectweb.asm.tree.MethodInsnNode');
    var InsnNode = Java.type('org.objectweb.asm.tree.InsnNode');
    var JumpInsnNode = Java.type('org.objectweb.asm.tree.JumpInsnNode');
    var LabelNode = Java.type('org.objectweb.asm.tree.LabelNode');
    return {
        'pixelmon_compass_waypoint': {
            'target': {'type': 'METHOD', 'class': 'com.chaosthedude.explorerscompass.connect.NewWayPoint', 'methodName': 'addPoint', 'methodDesc': '(IILnet/minecraft/entity/player/PlayerEntity;Ljava/lang/String;)V'},
            'transformer': function(method) {
                method.instructions.clear(); method.tryCatchBlocks.clear();
                if (method.localVariables != null) method.localVariables.clear();
                method.instructions.add(new VarInsnNode(Opcodes.ILOAD, 0));
                method.instructions.add(new VarInsnNode(Opcodes.ILOAD, 1));
                method.instructions.add(new VarInsnNode(Opcodes.ALOAD, 2));
                method.instructions.add(new VarInsnNode(Opcodes.ALOAD, 3));
                method.instructions.add(new MethodInsnNode(Opcodes.INVOKESTATIC, 'xaero/pixelmon/CompassCompat', 'addPoint', '(IILnet/minecraft/entity/player/PlayerEntity;Ljava/lang/String;)V', false));
                method.instructions.add(new InsnNode(Opcodes.RETURN));
                method.maxStack = 4; method.maxLocals = 4;
                return method;
            }
        },
        'pixelmon_compass_local_tick': {
            'target': {'type': 'METHOD', 'class': 'com.chaosthedude.explorerscompass.client.ClientEventHandler', 'methodName': 'onTick', 'methodDesc': '(Lnet/minecraftforge/event/TickEvent$PlayerTickEvent;)V'},
            'transformer': function(method) {
                var prefix = new InsnList(); var proceed = new LabelNode();
                prefix.add(new VarInsnNode(Opcodes.ALOAD, 1));
                prefix.add(new MethodInsnNode(Opcodes.INVOKESTATIC, 'xaero/pixelmon/CompassCompat', 'isLocalTick', '(Lnet/minecraftforge/event/TickEvent$PlayerTickEvent;)Z', false));
                prefix.add(new JumpInsnNode(Opcodes.IFNE, proceed));
                prefix.add(new InsnNode(Opcodes.RETURN)); prefix.add(proceed);
                method.instructions.insert(prefix);
                return method;
            }
        },
        'pixelmon_natures_compass_hud': {
            'target': {'type': 'METHOD', 'class': 'com.chaosthedude.naturescompass.util.RenderUtils', 'methodName': 'drawConfiguredStringOnHUD', 'methodDesc': '(Lcom/mojang/blaze3d/matrix/MatrixStack;Ljava/lang/String;IIII)V'},
            'transformer': function(method) {
                var prefix = new InsnList();
                prefix.add(new VarInsnNode(Opcodes.ILOAD, 3));
                prefix.add(new MethodInsnNode(Opcodes.INVOKESTATIC, 'xaero/pixelmon/CompassHud', 'natureYOffset', '(I)I', false));
                prefix.add(new VarInsnNode(Opcodes.ISTORE, 3));
                method.instructions.insert(prefix);
                return method;
            }
        }
    };
}
