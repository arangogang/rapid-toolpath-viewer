MODULE OffsTest
  CONST robtarget pBase := [[500,0,400],[1,0,0,0],[0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];

  PROC main()
    MoveL pBase, v100, fine, tool0;
    MoveL Offs(pBase, 0, 100, 0), v100, fine, tool0;
    MoveL Offs(pBase, 0, 200, 50), v100, z10, tool0;
  ENDPROC
ENDMODULE
